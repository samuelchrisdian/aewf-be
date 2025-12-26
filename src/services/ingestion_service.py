import pandas as pd
import datetime
import re
from src.app.extensions import db
from src.domain.models import (
    ImportBatch,
    Machine,
    MachineUser,
    AttendanceRawLog,
    AttendanceDaily,
    StudentMachineMap,
)
import logging
import json

logger = logging.getLogger(__name__)


class IngestionService:
    """
    Service for ingesting attendance log data from various file formats.

    Supports two formats:
    1. Traditional flat transactional log format (simple ID + Time columns)
    2. Matrix-style "Attendance Log Report" format with User Blocks
    """

    # Regex patterns for parsing the matrix attendance report
    TIME_PATTERN = re.compile(r"(\d{1,2}:\d{2})")
    # Pattern for "Stat.Date: 2025-08-01 ~ 2025-08-31" or "Att. Time  2025-08-01 ~ 2025-08-31"
    DATE_RANGE_PATTERN = re.compile(
        r"(\d{4}-\d{2}-\d{2})\s*~\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE
    )
    # Fallback pattern for single date
    SINGLE_DATE_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2})")

    @staticmethod
    def import_logs_from_excel(
        file_path: str, filename: str, machine_code: str
    ) -> dict:
        """
        Imports raw logs from attendance report files.

        Supports two formats:
        1. Traditional flat format with ID and Time columns
        2. Matrix-style "Attendance Log Report" with User Blocks

        Matrix Format Structure:
        - Metadata row contains "Stat.Date: 2025-08-01 ~ 2025-08-31"
        - User blocks start with "ID:" row containing user ID and name
        - Subsequent columns contain dates (1, 2, 3... 31)
        - Cell values may contain "mashed" times like "06:5815:03"

        Args:
            file_path: Path to the file (xlsx, xls, or csv)
            filename: Original filename for tracking
            machine_code: Machine code to associate logs with

        Returns:
            dict with batch_id, logs_imported count, and any errors
        """
        batch = ImportBatch(filename=filename, file_type="logs", status="processing")
        db.session.add(batch)
        db.session.flush()

        results = {"batch_id": batch.id, "logs_imported": 0, "errors": []}

        try:
            # Get Machine first
            machine = Machine.query.filter_by(machine_code=machine_code).first()
            if not machine:
                raise ValueError(
                    f"Machine {machine_code} not found. Running Sync Users first is recommended."
                )

            # Determine file type and read appropriately
            if file_path.lower().endswith(".csv"):
                df_raw = pd.read_csv(file_path, header=None, dtype=str)
            else:
                xl = pd.ExcelFile(file_path)
                # Find log sheet or use first sheet
                log_sheet = next(
                    (s for s in xl.sheet_names if "log" in s.lower()), xl.sheet_names[0]
                )
                df_raw = pd.read_excel(
                    file_path, sheet_name=log_sheet, header=None, dtype=str
                )

            # Detect format: check if it's matrix format (has "ID:" pattern) or flat format
            is_matrix_format = IngestionService._detect_matrix_format(df_raw)

            if is_matrix_format:
                count = IngestionService._parse_matrix_format(
                    df_raw, batch.id, machine, results
                )
            else:
                count = IngestionService._parse_flat_format(
                    file_path, batch.id, machine, results
                )

            batch.records_processed = count
            batch.status = (
                "completed" if not results["errors"] else "completed_with_errors"
            )
            batch.error_log = results["errors"] if results["errors"] else None

            results["logs_imported"] = count

            # Aggregate raw logs to daily attendance
            if count > 0:
                daily_count = IngestionService._aggregate_raw_logs_to_daily(
                    batch.id, results
                )
                results["daily_records_created"] = daily_count

            db.session.commit()
            return results

        except Exception as e:
            db.session.rollback()
            batch.status = "failed"
            batch.error_log = [str(e)]
            db.session.commit()
            raise e

    @staticmethod
    def _detect_matrix_format(df: pd.DataFrame) -> bool:
        """
        Detects if the dataframe is in matrix format by looking for "ID:" pattern.

        Args:
            df: Raw dataframe without headers

        Returns:
            True if matrix format detected, False otherwise
        """
        # Check first 50 rows for "ID:" pattern
        for idx in range(min(50, len(df))):
            first_cell = str(df.iloc[idx, 0]) if pd.notna(df.iloc[idx, 0]) else ""
            if first_cell.strip().upper().startswith("ID:"):
                return True
        return False

    @staticmethod
    def _extract_period_from_report(df: pd.DataFrame) -> tuple:
        """
        Extracts the Year and Month from the report metadata.

        Looks for patterns like:
        - "Stat.Date: 2025-08-01 ~ 2025-08-31"
        - "Att. Time: 2025-08-01"

        Args:
            df: Raw dataframe

        Returns:
            Tuple of (year, month) as integers, or (None, None) if not found
        """
        # Search first 20 rows for date metadata
        for idx in range(min(20, len(df))):
            row_text = " ".join([str(x) for x in df.iloc[idx] if pd.notna(x)])

            # Try date range pattern: "2025-08-01 ~ 2025-08-31"
            match = IngestionService.DATE_RANGE_PATTERN.search(row_text)
            if match:
                start_date = match.group(1)
                year, month, _ = start_date.split("-")
                logger.info(f"Found period from date range: {year}-{month}")
                return int(year), int(month)

            # Try single date pattern as fallback
            match = IngestionService.SINGLE_DATE_PATTERN.search(row_text)
            if match:
                date_str = match.group(1)
                year, month, _ = date_str.split("-")
                logger.info(f"Found period from single date: {year}-{month}")
                return int(year), int(month)

        logger.warning("Could not extract period from report metadata")
        return None, None

    @staticmethod
    def _parse_user_block_header(row: pd.Series) -> dict:
        """
        Parses a User Block header row to extract user information.

        Example row format:
        "ID:,,1,,,,,,Name:,,Shem,,,,,,Dept.:,,GTT..."

        Args:
            row: Pandas Series representing the row

        Returns:
            Dict with 'user_id', 'user_name', 'department' keys
        """
        user_info = {"user_id": None, "user_name": None, "department": None}

        # Convert row to string and find patterns
        row_values = [
            str(x).strip() for x in row.values if pd.notna(x) and str(x).strip()
        ]
        row_text = " ".join(row_values)

        # Parse ID
        id_match = re.search(r"ID:\s*[,\s]*(\d+)", row_text, re.IGNORECASE)
        if id_match:
            user_info["user_id"] = id_match.group(1)

        # Parse Name
        name_match = re.search(
            r"Name:\s*[,\s]*([A-Za-z\s]+?)(?:\s*(?:Dept\.|Department|,|$))",
            row_text,
            re.IGNORECASE,
        )
        if name_match:
            user_info["user_name"] = name_match.group(1).strip()

        # Parse Department
        dept_match = re.search(
            r"Dept\.?:\s*[,\s]*([A-Za-z0-9\s]+)", row_text, re.IGNORECASE
        )
        if dept_match:
            user_info["department"] = dept_match.group(1).strip()

        return user_info

    @staticmethod
    def _extract_times_from_cell(cell_value: str) -> list:
        """
        Extracts all valid times from a cell value.

        Handles "mashed" times like "06:5815:03" which should become ["06:58", "15:03"]
        Also handles normal times and ignores text like "Absent".

        Args:
            cell_value: String value from a cell

        Returns:
            List of time strings in HH:MM format
        """
        if not cell_value or pd.isna(cell_value):
            return []

        cell_str = str(cell_value).strip()

        # Skip known non-time values
        skip_patterns = ["absent", "leave", "sick", "holiday", "off", "nan", ""]
        if cell_str.lower() in skip_patterns:
            return []

        # Find all time patterns
        times = IngestionService.TIME_PATTERN.findall(cell_str)

        # Validate and normalize times
        valid_times = []
        for time_str in times:
            try:
                # Normalize to HH:MM format
                parts = time_str.split(":")
                hour = int(parts[0])
                minute = int(parts[1])

                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    valid_times.append(f"{hour:02d}:{minute:02d}")
            except (ValueError, IndexError):
                continue

        return valid_times

    @staticmethod
    def _find_day_column_mapping(df: pd.DataFrame, header_row_idx: int) -> dict:
        """
        Finds the mapping between column indices and day numbers.

        The matrix format has columns representing days 1-31.
        This function identifies which column corresponds to which day.

        Args:
            df: Raw dataframe
            header_row_idx: Index of the header row containing day numbers

        Returns:
            Dict mapping column index to day number
        """
        day_map = {}

        if header_row_idx is None or header_row_idx >= len(df):
            # Try to find header automatically - look for row with numbers 1-31
            for idx in range(min(20, len(df))):
                row = df.iloc[idx]
                day_count = 0
                temp_map = {}

                for col_idx, val in enumerate(row):
                    if pd.notna(val):
                        try:
                            day = int(float(str(val).strip()))
                            if 1 <= day <= 31:
                                temp_map[col_idx] = day
                                day_count += 1
                        except (ValueError, TypeError):
                            continue

                # If we found enough days, use this row
                if day_count >= 7:  # At least a week's worth
                    day_map = temp_map
                    logger.info(
                        f"Found day column mapping at row {idx}: {len(day_map)} days"
                    )
                    break
        else:
            # Use specified header row
            row = df.iloc[header_row_idx]
            for col_idx, val in enumerate(row):
                if pd.notna(val):
                    try:
                        day = int(float(str(val).strip()))
                        if 1 <= day <= 31:
                            day_map[col_idx] = day
                    except (ValueError, TypeError):
                        continue

        return day_map

    @staticmethod
    def _parse_matrix_format(
        df: pd.DataFrame, batch_id: int, machine, results: dict
    ) -> int:
        """
        Parses the matrix-style attendance report format.

        Uses a state machine approach:
        1. Extract period (year, month) from metadata
        2. Find day column mapping
        3. Iterate rows, detecting User Block headers ("ID:")
        4. For each user, parse time data from subsequent day columns
        5. Create AttendanceRawLog entries for each extracted time

        Args:
            df: Raw dataframe without headers
            batch_id: ImportBatch ID for linking records
            machine: Machine object
            results: Dict to append errors to

        Returns:
            Count of successfully imported log entries
        """
        count = 0

        # Step 1: Extract period
        year, month = IngestionService._extract_period_from_report(df)
        if year is None or month is None:
            # Try to infer from current date as fallback
            now = datetime.datetime.now()
            year, month = now.year, now.month
            results["errors"].append(
                f"Warning: Could not find period in report, using current date: {year}-{month}"
            )

        # Step 2: Find day column mapping
        day_map = IngestionService._find_day_column_mapping(df, None)
        if not day_map:
            raise ValueError(
                "Could not find day column mapping in the report. Expected columns with day numbers (1-31)."
            )

        logger.info(
            f"Parsing matrix format - Period: {year}-{month}, Day columns: {len(day_map)}"
        )

        # Step 3: State machine - iterate through rows
        current_user_id = None
        current_user_info = None
        current_machine_user = None

        for row_idx in range(len(df)):
            row = df.iloc[row_idx]
            first_cell = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""

            # Check if this is a User Block header
            if first_cell.upper().startswith("ID:"):
                # Parse user info from this row
                user_info = IngestionService._parse_user_block_header(row)
                current_user_id = user_info["user_id"]
                current_user_info = user_info

                if not current_user_id:
                    results["errors"].append(
                        f"Row {row_idx}: Could not extract user ID from header row"
                    )
                    current_machine_user = None
                    continue

                # FILTER: Only process users from SMP department
                department = user_info.get("department", "").upper()
                if department and department != "SMP":
                    logger.debug(
                        f"Skipping user ID={current_user_id}, Department={department} (not SMP)"
                    )
                    current_machine_user = None
                    continue

                # Lookup MachineUser
                current_machine_user = MachineUser.query.filter_by(
                    machine_id=machine.id, machine_user_id=current_user_id
                ).first()

                if not current_machine_user:
                    results["errors"].append(
                        f"Row {row_idx}: User ID {current_user_id} ({user_info.get('user_name', 'Unknown')}) "
                        f"not found in machine {machine.machine_code}"
                    )

                logger.debug(
                    f"Found user block: ID={current_user_id}, Name={user_info.get('user_name')}, Dept={department}"
                )
                continue

            # If we have a valid user, try to parse time data from this row
            if current_machine_user and day_map:
                row_has_times = False

                for col_idx, day in day_map.items():
                    if col_idx >= len(row):
                        continue

                    cell_value = row.iloc[col_idx]
                    times = IngestionService._extract_times_from_cell(cell_value)

                    if times:
                        row_has_times = True

                        # Create datetime for each extracted time
                        for time_str in times:
                            try:
                                hour, minute = map(int, time_str.split(":"))

                                # Create the full datetime
                                try:
                                    event_datetime = datetime.datetime(
                                        year=year,
                                        month=month,
                                        day=day,
                                        hour=hour,
                                        minute=minute,
                                    )
                                except ValueError as date_err:
                                    # Invalid date (e.g., Feb 30)
                                    results["errors"].append(
                                        f"Row {row_idx}, Day {day}: Invalid date {year}-{month}-{day} {time_str}: {date_err}"
                                    )
                                    continue

                                # Create AttendanceRawLog entry
                                log_entry = AttendanceRawLog(
                                    batch_id=batch_id,
                                    machine_user_id_fk=current_machine_user.id,
                                    event_time=event_datetime,
                                    raw_data={
                                        "user_id": current_user_id,
                                        "user_name": current_user_info.get("user_name"),
                                        "department": current_user_info.get(
                                            "department"
                                        ),
                                        "day": day,
                                        "time": time_str,
                                        "raw_cell": str(cell_value),
                                        "source_row": row_idx,
                                    },
                                )
                                db.session.add(log_entry)
                                count += 1

                            except Exception as time_err:
                                results["errors"].append(
                                    f"Row {row_idx}, Day {day}, Time {time_str}: {str(time_err)}"
                                )

                # If row has no times and doesn't look like metadata, it might be a new section
                if (
                    not row_has_times
                    and first_cell
                    and not any(
                        keyword in first_cell.lower()
                        for keyword in [
                            "id:",
                            "name:",
                            "dept",
                            "stat",
                            "att",
                            "total",
                            "date",
                        ]
                    )
                ):
                    # Could be end of user block or data row without times
                    pass

        logger.info(f"Matrix format parsing complete: {count} log entries created")
        return count

    @staticmethod
    def _parse_flat_format(
        file_path: str, batch_id: int, machine, results: dict
    ) -> int:
        """
        Parses the traditional flat transactional log format.

        Expects columns: ID, Time/DateTime/Waktu

        Args:
            file_path: Path to the file
            batch_id: ImportBatch ID for linking records
            machine: Machine object
            results: Dict to append errors to

        Returns:
            Count of successfully imported log entries
        """
        count = 0

        # Determine file type
        if file_path.lower().endswith(".csv"):
            df_preview = pd.read_csv(file_path, header=None, nrows=20)
        else:
            xl = pd.ExcelFile(file_path)
            log_sheet = next(
                (s for s in xl.sheet_names if "log" in s.lower()), xl.sheet_names[0]
            )
            df_preview = pd.read_excel(
                file_path, sheet_name=log_sheet, header=None, nrows=20
            )

        # Find header row
        header_row_idx = None
        for idx, row in df_preview.iterrows():
            row_val = [str(x).lower().strip() for x in row.values if pd.notna(x)]
            if "id" in row_val and any(
                x in row_val for x in ["time", "datetime", "waktu"]
            ):
                header_row_idx = idx
                break

        if header_row_idx is None:
            raise ValueError("Could not find table header (ID, Time) in Log sheet.")

        # Read full data with proper header
        if file_path.lower().endswith(".csv"):
            df = pd.read_csv(file_path, header=header_row_idx)
        else:
            df = pd.read_excel(file_path, sheet_name=log_sheet, header=header_row_idx)

        df.columns = [str(c).strip() for c in df.columns]

        # Find columns
        id_col = next((c for c in df.columns if c.lower() == "id"), None)
        time_col = next(
            (c for c in df.columns if c.lower() in ["datetime", "time", "waktu"]), None
        )

        if not id_col or not time_col:
            raise ValueError("Missing ID or Time column in Log sheet.")

        # Import logs
        for index, row in df.iterrows():
            try:
                uid = row[id_col]
                if pd.isna(uid):
                    continue

                uid_str = str(int(uid)) if isinstance(uid, float) else str(uid)

                # Parse Time
                raw_time = row[time_col]
                event_time = pd.to_datetime(raw_time)

                # Verify MachineUser
                m_user = MachineUser.query.filter_by(
                    machine_id=machine.id, machine_user_id=uid_str
                ).first()

                if not m_user:
                    results["errors"].append(
                        f"Row {index}: User {uid_str} not found in machine {machine.machine_code}"
                    )
                    continue

                # Create Raw Log
                log_entry = AttendanceRawLog(
                    batch_id=batch_id,
                    machine_user_id_fk=m_user.id,
                    event_time=event_time,
                    raw_data=json.loads(row.to_json()),
                )
                db.session.add(log_entry)
                count += 1

            except Exception as row_err:
                results["errors"].append(f"Row {index}: {str(row_err)}")

        return count

    @staticmethod
    def _aggregate_raw_logs_to_daily(batch_id: int, results: dict) -> int:
        """
        Aggregates raw attendance logs into daily attendance records.

        For each machine_user on each day:
        1. Find the student mapping (student_machine_map)
        2. Get earliest scan as check_in, latest scan as check_out
        3. Determine status based on check_in time
        4. Create/update AttendanceDaily record

        Args:
            batch_id: ImportBatch ID to process
            results: Dict to append errors to

        Returns:
            Count of daily records created/updated
        """
        count = 0

        # Get all raw logs for this batch
        raw_logs = AttendanceRawLog.query.filter_by(batch_id=batch_id).all()

        if not raw_logs:
            return 0

        # Group logs by (machine_user_id_fk, date)
        daily_data = {}  # {(machine_user_id, date): [log1, log2, ...]}

        for log in raw_logs:
            event_date = log.event_time.date()
            key = (log.machine_user_id_fk, event_date)

            if key not in daily_data:
                daily_data[key] = []
            daily_data[key].append(log)

        logger.info(
            f"Aggregating {len(raw_logs)} raw logs into {len(daily_data)} daily records"
        )

        # Process each day's logs
        for (machine_user_id_fk, event_date), logs in daily_data.items():
            try:
                # Find student mapping
                mapping = StudentMachineMap.query.filter_by(
                    machine_user_id_fk=machine_user_id_fk,
                    status="verified",  # Only use verified mappings
                ).first()

                # Also try suggested mappings if no verified found
                if not mapping:
                    mapping = StudentMachineMap.query.filter_by(
                        machine_user_id_fk=machine_user_id_fk, status="suggested"
                    ).first()

                if not mapping:
                    # Skip if no mapping found
                    machine_user = MachineUser.query.get(machine_user_id_fk)
                    if machine_user:
                        results["errors"].append(
                            f"No student mapping for machine user ID {machine_user.machine_user_id} "
                            f"({machine_user.machine_user_name}) on {event_date}"
                        )
                    continue

                student_nis = mapping.student_nis

                # Sort logs by time to get earliest and latest
                sorted_logs = sorted(logs, key=lambda x: x.event_time)
                check_in_time = sorted_logs[0].event_time
                check_out_time = (
                    sorted_logs[-1].event_time if len(sorted_logs) > 1 else None
                )

                # Determine status based on check-in time
                # Assume: 07:00 = on time, 07:01-07:30 = late, after 07:30 = very late
                check_in_hour = check_in_time.hour
                check_in_minute = check_in_time.minute

                if check_in_hour < 7:
                    status = "present"
                elif check_in_hour == 7 and check_in_minute == 0:
                    status = "present"
                elif check_in_hour == 7 and check_in_minute <= 30:
                    status = "late"
                else:
                    status = "late"

                # Check if attendance record already exists
                existing = AttendanceDaily.query.filter_by(
                    student_nis=student_nis, attendance_date=event_date
                ).first()

                if existing:
                    # Update existing record
                    existing.check_in = check_in_time
                    existing.check_out = check_out_time
                    existing.status = status
                else:
                    # Create new record
                    daily_record = AttendanceDaily(
                        student_nis=student_nis,
                        attendance_date=event_date,
                        check_in=check_in_time,
                        check_out=check_out_time,
                        status=status,
                    )
                    db.session.add(daily_record)
                    count += 1

            except Exception as e:
                results["errors"].append(
                    f"Error aggregating logs for machine_user {machine_user_id_fk} on {event_date}: {str(e)}"
                )

        logger.info(f"Created {count} new daily attendance records")
        return count
