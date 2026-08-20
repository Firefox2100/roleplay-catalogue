"""Convert Vitest's JUnit report to SonarQube's generic test format."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path, PurePosixPath
import xml.etree.ElementTree as ET


def _sonar_path(classname: str) -> str:
    path = PurePosixPath(classname.replace("\\", "/"))
    if path.parts and path.parts[0] == "frontend":
        return str(path)
    return str(PurePosixPath("frontend") / path)


def convert(input_path: Path, output_path: Path) -> None:
    junit = ET.parse(input_path).getroot()
    cases_by_file: dict[str, list[ET.Element]] = defaultdict(list)

    for case in junit.iter("testcase"):
        classname = case.get("classname")
        if not classname:
            raise ValueError("Every JUnit testcase must have a classname")
        cases_by_file[_sonar_path(classname)].append(case)

    executions = ET.Element("testExecutions", version="1")
    for filename, cases in sorted(cases_by_file.items()):
        file_element = ET.SubElement(executions, "file", path=filename)
        for case in cases:
            duration = round(float(case.get("time", "0")) * 1000)
            test_case = ET.SubElement(
                file_element,
                "testCase",
                name=case.get("name", "unnamed test"),
                duration=str(duration),
            )
            for result_type in ("failure", "error", "skipped"):
                result = case.find(result_type)
                if result is not None:
                    converted = ET.SubElement(
                        test_case,
                        result_type,
                        message=result.get("message", result_type),
                    )
                    converted.text = result.text
                    break

    ET.indent(executions)
    ET.ElementTree(executions).write(output_path, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    convert(args.input, args.output)
