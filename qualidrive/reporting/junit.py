"""
JUnit XML report generator for CI/CD qualification integration.
"""

import xml.etree.ElementTree as ET
from typing import List, Dict, Any


def generate_junit_xml(results: List[Dict[str, Any]], run_id: str) -> str:
    """Generates standard JUnit XML string representing qualification suite results."""
    testsuites = ET.Element("testsuites", name="QualiDrive", id=run_id)

    total_tests = len(results)
    failures = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] in ("ERROR", "TIMEOUT"))
    skipped = sum(1 for r in results if r["status"] == "BLOCKED_BY_SAFETY")
    total_time = sum(float(r.get("duration_sec", 0.0)) for r in results)

    suite = ET.SubElement(
        testsuites,
        "testsuite",
        name="NVMe_Qualification",
        tests=str(total_tests),
        failures=str(failures),
        errors=str(errors),
        skipped=str(skipped),
        time=f"{total_time:.2f}"
    )

    for r in results:
        case_id = r["case_id"]
        status = r["status"]
        duration = str(r.get("duration_sec", 0.0))

        tc = ET.SubElement(
            suite,
            "testcase",
            classname="qualidrive.qualification_matrix",
            name=case_id,
            time=duration
        )

        if status == "FAIL":
            fail_el = ET.SubElement(tc, "failure", message="Qualification threshold breached")
            details = []
            for th in r.get("thresholds", []):
                if not th["passed"]:
                    details.append(f"{th['metric']}: {th['observed']} {th['operator']} {th['threshold']} ({th['details']})")
            fail_el.text = "\n".join(details) if details else r.get("error_message", "Failed")

        elif status in ("ERROR", "TIMEOUT"):
            err_el = ET.SubElement(tc, "error", message=f"Test encountered {status}")
            err_el.text = r.get("error_message", f"Execution aborted with status {status}")

        elif status == "BLOCKED_BY_SAFETY":
            skip_el = ET.SubElement(tc, "skipped", message="Safety guardrail blocked execution")
            skip_el.text = r.get("error_message", "Blocked by safety checks")

    return ET.tostring(testsuites, encoding="utf-8", xml_declaration=True).decode("utf-8")
