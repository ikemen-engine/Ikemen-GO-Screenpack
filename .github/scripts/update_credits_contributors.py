#!/usr/bin/env python3
"""Generate the Ikemen GO developer section in data/ikemen1/credits.def."""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, TypedDict

CREDITS_PATH = Path("data/ikemen1/credits.def")
SOURCE_REPOSITORY = "ikemen-engine/Ikemen-GO"
MIN_COMMITS = 2
MIN_ADDITIONS = 100
GENERATED_FIRST_LAYER = 5
COLLECTIVE_TEXT = "Among many other Ikemen GO engine contributors"

# Keep preferred public nicknames from the existing credits instead of exposing
# a different GitHub login/capitalization when one is known.
DISPLAY_NAMES = {
    "ambonmibable": "Wintermourn",
    "assemblaj": "fantasma",
    "danielporto": "Daniel Porto",
    "facundocameto": "Kase",
	"kasasagi77": "Kasasagi",
    "lazin3ss": "Wreq!",
    "leonkasovan": "Leon Kasovan",
    "nckgriva": "Nikolay Griva",
    "omegashironeko": "Ohmga Shironeko",
    "potsmugen": "PotS",
    "rakieldev": "Rakíel",
    "realfoobs": "Foobs",
    "samhocevar": "Sam Hocevar",
    "superfromnd": "Super",
    "windblade-gr01": "Gacel",
}

EXCLUDED_LOGINS = {
    "k4thos",
    "lint-action",
    "ppitulaj",
    "suehiro",
}

API_VERSION = "2022-11-28"
STATS_RETRIES = 12
STATS_RETRY_SECONDS = 5

LAYER_PROPERTY_RE = re.compile(r"^(?P<prefix>\s*layer)(?P<number>\d+)(?P<suffix>\.[^=]+?\s*=\s*)(?P<value>.*)$")
STARTTIME_VALUE_RE = re.compile(r"^(?P<space>\s*)(?P<value>-?\d+)(?P<trailing>\s*)$")
END_TIME_RE = re.compile(r"^(?P<prefix>\s*end\.time\s*=\s*)(?P<value>-?\d+)(?P<trailing>\s*)$")


class Contributor(TypedDict):
    login: str
    commits: int
    additions: int


def request_json(
    token: str,
    url: str,
    *,
    accepted_statuses: set[int] = {200},
) -> tuple[int, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "ikemen-go-screenpack-credits-generator",
            "X-GitHub-Api-Version": API_VERSION,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            status = response.status
            if status not in accepted_statuses:
                raise RuntimeError(f"GitHub API returned unexpected HTTP {status}")
            if status in {202, 204}:
                return status, None
            return status, json.load(response)
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API returned HTTP {exc.code}: {details}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GitHub API request failed: {exc}") from exc


def fetch_contributor_stats(token: str, repository: str) -> list[dict[str, Any]]:
    url = f"https://api.github.com/repos/{repository}/stats/contributors"

    for attempt in range(STATS_RETRIES):
        status, data = request_json(token, url, accepted_statuses={200, 202, 204})
        if status == 200:
            return data
        if status == 204:
            return []
        if attempt + 1 < STATS_RETRIES:
            print("Contributor statistics are being generated; retrying...")
            time.sleep(STATS_RETRY_SECONDS)

    raise RuntimeError("GitHub did not finish generating contributor statistics")


def collect_contributors(stats: list[dict[str, Any]]) -> list[Contributor]:
    excluded = {login.casefold() for login in EXCLUDED_LOGINS}
    contributors: list[Contributor] = []

    for item in stats:
        author = item.get("author")
        if author is None:
            continue

        login = author["login"]
        key = login.casefold()
        if author.get("type") == "Bot" or key.endswith("[bot]") or key in excluded:
            continue

        weeks = item["weeks"]
        contributors.append(
            {
                "login": login,
                "commits": item["total"],
                "additions": sum(week["a"] for week in weeks),
            }
        )

    return contributors


def qualifies(contributor: Contributor) -> bool:
    return contributor["commits"] >= MIN_COMMITS and contributor["additions"] >= MIN_ADDITIONS


def display_name(login: str) -> str:
    return DISPLAY_NAMES.get(login.casefold(), login)


def generated_contributors(
    contributors: list[Contributor],
) -> tuple[list[Contributor], list[Contributor]]:
    included: list[Contributor] = []
    skipped: list[Contributor] = []

    for contributor in contributors:
        if qualifies(contributor):
            included.append(contributor)
        else:
            skipped.append(contributor)

    included.sort(
        key=lambda item: (
            -item["additions"],
            -item["commits"],
            display_name(item["login"]).casefold(),
        )
    )
    return included, skipped


def layer_block(number: int, text: str, starttime: int, *, heading: bool) -> list[str]:
    return [
        f'layer{number}.text = "{text}"',
        f"layer{number}.starttime = {starttime}",
        f"layer{number}.font = {0 if heading else 1}",
        f"layer{number}.offset = 0,20",
        f"layer{number}.velocity = 0,-2",
        f"layer{number}.textdelay = {3 if heading else 2}",
    ]


def generate_section(
    contributors: list[Contributor],
    *,
    first_layer: int,
    first_starttime: int,
) -> tuple[list[str], int, int]:
    lines: list[str] = []
    lines.extend(layer_block(first_layer, "DEVELOPERS", first_starttime, heading=True))

    layer = first_layer + 1
    starttime = first_starttime + 40
    for contributor in contributors:
        lines.append("")
        lines.extend(
            layer_block(
                layer,
                display_name(contributor["login"]),
                starttime,
                heading=False,
            )
        )
        layer += 1
        starttime += 30

    lines.append("")
    lines.extend(layer_block(layer, COLLECTIVE_TEXT, starttime, heading=False))
    return lines, layer, starttime


def find_layer_value(lines: list[str], layer: int, property_name: str) -> int:
    pattern = re.compile(rf"^\s*layer{layer}\.{re.escape(property_name)}\s*=\s*(-?\d+)\s*$")
    for line in lines:
        match = pattern.match(line)
        if match:
            return int(match.group(1))
    raise RuntimeError(f"Could not find layer{layer}.{property_name} in {CREDITS_PATH}")


def shift_tail(
    lines: list[str],
    *,
    old_collective_layer: int,
    layer_delta: int,
    time_delta: int,
) -> list[str]:
    shifted: list[str] = []
    in_scene_2 = True

    for original_line in lines:
        line = original_line
        if line.strip() == "[Scene 3]":
            in_scene_2 = False

        layer_match = LAYER_PROPERTY_RE.match(line)
        if layer_match:
            old_layer = int(layer_match.group("number"))
            if old_layer > old_collective_layer:
                value = layer_match.group("value")
                property_name = layer_match.group("suffix").split("=", 1)[0].strip().lstrip(".")
                if property_name == "starttime":
                    value_match = STARTTIME_VALUE_RE.match(value)
                    if not value_match:
                        raise RuntimeError(f"Unexpected starttime value: {original_line}")
                    value = (
                        f"{value_match.group('space')}"
                        f"{int(value_match.group('value')) + time_delta}"
                        f"{value_match.group('trailing')}"
                    )
                line = (
                    f"{layer_match.group('prefix')}"
                    f"{old_layer + layer_delta}"
                    f"{layer_match.group('suffix')}"
                    f"{value}"
                )

        if in_scene_2:
            end_match = END_TIME_RE.match(line)
            if end_match:
                line = (
                    f"{end_match.group('prefix')}"
                    f"{int(end_match.group('value')) + time_delta}"
                    f"{end_match.group('trailing')}"
                )

        shifted.append(line)

    return shifted


def update_credits(contributors: list[Contributor]) -> bool:
    text = CREDITS_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()

    generated_start = next(
        (
            index
            for index, line in enumerate(lines)
            if re.match(rf"^\s*layer{GENERATED_FIRST_LAYER}\.", line)
        ),
        None,
    )
    if generated_start is None:
        raise RuntimeError(f"Could not find layer{GENERATED_FIRST_LAYER} in {CREDITS_PATH}")

    collective_match = None
    collective_text_index = None
    for index in range(generated_start, len(lines)):
        match = re.match(
            rf'^\s*layer(?P<number>\d+)\.text\s*=\s*"{re.escape(COLLECTIVE_TEXT)}"\s*$',
            lines[index],
        )
        if match:
            collective_match = match
            collective_text_index = index
            break
    if collective_match is None or collective_text_index is None:
        raise RuntimeError(f"Could not find the generated credits boundary in {CREDITS_PATH}")

    old_collective_layer = int(collective_match.group("number"))
    old_section = lines[generated_start:]
    first_starttime = find_layer_value(old_section, GENERATED_FIRST_LAYER, "starttime")
    old_collective_starttime = find_layer_value(old_section, old_collective_layer, "starttime")

    generated_end = collective_text_index + 1
    while generated_end < len(lines) and re.match(
        rf"^\s*layer{old_collective_layer}\.", lines[generated_end]
    ):
        generated_end += 1

    included, skipped = generated_contributors(contributors)
    generated_lines, new_collective_layer, new_collective_starttime = generate_section(
        included,
        first_layer=GENERATED_FIRST_LAYER,
        first_starttime=first_starttime,
    )

    layer_delta = new_collective_layer - old_collective_layer
    time_delta = new_collective_starttime - old_collective_starttime
    tail = shift_tail(
        lines[generated_end:],
        old_collective_layer=old_collective_layer,
        layer_delta=layer_delta,
        time_delta=time_delta,
    )

    updated = "\n".join(lines[:generated_start] + generated_lines + tail) + "\n"
    if updated == text:
        print_audit(included, skipped)
        return False

    CREDITS_PATH.write_text(updated, encoding="utf-8", newline="\n")
    print_audit(included, skipped)
    return True


def print_audit(
    included: list[Contributor],
    skipped: list[Contributor],
) -> None:
    print(
        f"Policy: >= {MIN_COMMITS} non-merge commits and >= {MIN_ADDITIONS} "
        f"cumulative additions in {SOURCE_REPOSITORY}."
    )
    print("\nGenerated DEVELOPERS (highest additions first):")
    for contributor in included:
        print(
            f"  {display_name(contributor['login'])} [{contributor['login']}]: "
            f"{contributor['commits']} commits, {contributor['additions']} additions"
        )

    print("\nBelow threshold (covered by the collective credit):")
    for contributor in sorted(skipped, key=lambda item: item["login"].casefold()):
        print(
            f"  {display_name(contributor['login'])}: "
            f"{contributor['commits']} commits, {contributor['additions']} additions"
        )


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN")
    repository = os.environ.get("IKEMEN_GO_REPOSITORY", SOURCE_REPOSITORY)
    if not token:
        print("GITHUB_TOKEN is required", file=sys.stderr)
        return 2

    try:
        stats = fetch_contributor_stats(token, repository)
        contributors = collect_contributors(stats)
        changed = update_credits(contributors)
    except (RuntimeError, ValueError, KeyError, TypeError) as exc:
        print(exc, file=sys.stderr)
        return 1

    print("\ncredits.def updated." if changed else "\ncredits.def is already current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
