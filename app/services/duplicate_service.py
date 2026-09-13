from typing import List, Dict, Any, Set, Optional


class DuplicateService:
    """Service to detect potential duplicate records across pages or documents."""

    @staticmethod
    def identify_duplicates_in_batch(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect duplicates within a single page/batch based on ID number or serial number.
        Flags records without automatically deleting them to preserve audit evidence.
        """
        seen_ids: Set[str] = set()
        seen_serials: Set[int] = set()

        for rec in records:
            id_num = rec.get("id_number")
            serial = rec.get("serial_number")

            is_dup = False
            if id_num and id_num in seen_ids:
                is_dup = True
            elif serial is not None and serial in seen_serials:
                is_dup = True

            if is_dup:
                rec["is_duplicate"] = True
                if rec.get("validation_status") == "VALID":
                    rec["validation_status"] = "WARNING"
            else:
                rec["is_duplicate"] = False
                if id_num:
                    seen_ids.add(id_num)
                if serial is not None:
                    seen_serials.add(serial)

        return records
