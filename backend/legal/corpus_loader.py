"""Legal corpus ingestion and processing.

Scrapes IPC and BNS sections from indiacode.nic.in, parses structure,
and prepares data for RAG indexing.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("chakravyuha.legal.corpus")


@dataclass
class Section:
    """Represents a legal section (IPC/BNS/etc.)."""

    section_id: str  # e.g., "IPC-152", "BNS-103"
    act: str  # e.g., "Indian Penal Code", "Bharatiya Nyaya Sanhita"
    act_short: str  # e.g., "IPC", "BNS"
    year: int  # Year of enactment
    chapter: Optional[str]  # Chapter name
    section_number: str  # e.g., "152"
    title: str  # Section title
    description: str  # Full text
    punishment: Optional[str]  # Punishment details
    illustrations: Optional[list[str]]  # Example cases
    relevant_subsections: Optional[list[str]]  # Linked sections
    court_type: str  # "Sessions Court" or "Magistrate Court"
    tags: list[str]  # Searchable tags (e.g., ["violence", "assault"])

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


class CorpusLoader:
    """Load and process legal corpus from indiacode.nic.in."""

    BASE_URL = "https://indiacode.nis.gov.in"
    IPC_URL = f"{BASE_URL}/show-data?actid=4&sectionid=1&searchurl=section"
    BNS_URL = f"{BASE_URL}/show-data?actid=49&sectionid=1&searchurl=section"

    # Regex patterns
    SECTION_PATTERN = r"^Section\s+(\d+[A-Z]?)\s*[:-]\s*(.*?)$"
    PUNISHMENT_PATTERN = r"(?:shall\s+be\s+)?punish(?:able)?.*?(?:with|by)(.+?)(?:or|and|$)"

    def __init__(self, cache_dir: Path = Path("data/corpus_cache")):
        """Initialize corpus loader.

        Args:
            cache_dir: Directory to cache downloaded data
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Chakravyuha Legal AI (Mozilla/5.0)"
        })

    def scrape_sections(
        self,
        act_name: str,
        act_short: str,
        year: int,
        url: str | None = None,
    ) -> list[Section]:
        """Scrape all sections of an act.

        Args:
            act_name: Full act name (e.g., "Indian Penal Code")
            act_short: Act shorthand (e.g., "IPC")
            year: Year of enactment
            url: Custom URL to scrape (optional)

        Returns:
            List of Section objects
        """
        if act_short == "IPC":
            url = url or self.IPC_URL
        elif act_short == "BNS":
            url = url or self.BNS_URL
        else:
            if not url:
                logger.warning(f"No default URL for {act_short}, skipping")
                return []

        logger.info(f"Scraping {act_short} sections from {url}...")

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return []

        # Parse HTML
        soup = BeautifulSoup(response.content, "html.parser")

        # Find all section elements (structure varies by act)
        sections = []
        section_divs = soup.find_all("div", class_="section-content")

        for div in section_divs:
            try:
                section = self._parse_section(div, act_name, act_short, year)
                if section:
                    sections.append(section)
            except Exception as e:
                logger.warning(f"Failed to parse section: {e}")

        logger.info(f"Scraped {len(sections)} sections from {act_short}")
        return sections

    def _parse_section(
        self,
        div: BeautifulSoup,
        act_name: str,
        act_short: str,
        year: int,
    ) -> Section | None:
        """Parse a single section div.

        Args:
            div: BeautifulSoup div element
            act_name: Act name
            act_short: Act shorthand
            year: Year of enactment

        Returns:
            Section object or None if parsing fails
        """
        # Extract section number and title
        heading = div.find("h3", class_="section-heading")
        if not heading:
            return None

        heading_text = heading.get_text(strip=True)
        match = re.match(self.SECTION_PATTERN, heading_text)
        if not match:
            return None

        section_number, title = match.groups()
        section_id = f"{act_short}-{section_number}"

        # Extract description
        description_div = div.find("div", class_="section-text")
        description = description_div.get_text(strip=True) if description_div else ""

        # Extract punishment (heuristic)
        punishment = self._extract_punishment(description)

        # Extract illustrations
        illustrations = self._extract_illustrations(description)

        # Extract relevant subsections (heuristic)
        relevant_subsections = self._extract_subsections(description)

        # Determine court type (heuristic based on section content)
        court_type = self._determine_court_type(description)

        # Generate tags (heuristic)
        tags = self._generate_tags(section_number, title, description)

        return Section(
            section_id=section_id,
            act=act_name,
            act_short=act_short,
            year=year,
            chapter=None,  # TODO: Extract from page structure
            section_number=section_number,
            title=title,
            description=description,
            punishment=punishment,
            illustrations=illustrations,
            relevant_subsections=relevant_subsections,
            court_type=court_type,
            tags=tags,
        )

    def _extract_punishment(self, text: str) -> str | None:
        """Extract punishment clause from section text."""
        match = re.search(self.PUNISHMENT_PATTERN, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()[:200]  # Truncate to 200 chars
        return None

    def _extract_illustrations(self, text: str) -> list[str]:
        """Extract illustrations/examples from section text."""
        illustrations = []
        # Split by "Illustration" keyword
        parts = re.split(r"Illustration\s*[:\.]", text, flags=re.IGNORECASE)
        for part in parts[1:]:  # Skip first part (main text)
            # Extract first ~150 chars of each illustration
            illustration = part.strip()[:150]
            if illustration:
                illustrations.append(illustration)
        return illustrations[:3]  # Limit to 3 illustrations

    def _extract_subsections(self, text: str) -> list[str]:
        """Extract references to subsections."""
        # Find patterns like "(1)", "(2)", "sub-section (3)"
        matches = re.findall(r"\(([0-9]+)\)", text)
        return list(set([f"({m})" for m in matches]))[:5]

    def _determine_court_type(self, text: str) -> str:
        """Heuristically determine if Sessions or Magistrate court."""
        high_severity_keywords = ["death penalty", "life imprisonment", "murder", "rape"]
        if any(keyword in text.lower() for keyword in high_severity_keywords):
            return "Sessions Court"
        return "Magistrate Court"

    def _generate_tags(self, section_number: str, title: str, text: str) -> list[str]:
        """Generate searchable tags."""
        tags = []
        text_lower = (title + " " + text).lower()

        # Crime categories
        crime_keywords = {
            "violence": ["assault", "hurt", "violence", "attack", "hit"],
            "theft": ["theft", "stolen", "robbery", "burglar", "larceny"],
            "property": ["property", "damage", "trespass", "encroach"],
            "sexual": ["rape", "sexual", "indecent", "molestation"],
            "fraud": ["fraud", "cheating", "misrepresentation", "forgery"],
            "murder": ["murder", "homicide", "kill", "death"],
            "traffic": ["traffic", "motor vehicle", "rash", "negligent"],
        }

        for tag, keywords in crime_keywords.items():
            if any(kw in text_lower for kw in keywords):
                tags.append(tag)

        return tags

    def save_corpus(self, sections: list[Section], output_file: Path):
        """Save sections to JSON file."""
        data = [s.to_dict() for s in sections]
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(sections)} sections to {output_file}")

    def load_corpus(self, input_file: Path) -> list[Section]:
        """Load sections from JSON file."""
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        sections = [Section(**item) for item in data]
        logger.info(f"Loaded {len(sections)} sections from {input_file}")
        return sections


def build_corpus():
    """Build complete legal corpus (IPC + BNS)."""
    loader = CorpusLoader()

    # Load or scrape IPC
    ipc_file = loader.cache_dir / "ipc_sections.json"
    if ipc_file.exists():
        logger.info("Loading cached IPC sections...")
        ipc_sections = loader.load_corpus(ipc_file)
    else:
        logger.info("Scraping IPC sections (this may take a few minutes)...")
        ipc_sections = loader.scrape_sections(
            "Indian Penal Code", "IPC", 1860
        )
        loader.save_corpus(ipc_sections, ipc_file)

    # Load or scrape BNS
    bns_file = loader.cache_dir / "bns_sections.json"
    if bns_file.exists():
        logger.info("Loading cached BNS sections...")
        bns_sections = loader.load_corpus(bns_file)
    else:
        logger.info("Scraping BNS sections...")
        bns_sections = loader.scrape_sections(
            "Bharatiya Nyaya Sanhita", "BNS", 2023
        )
        loader.save_corpus(bns_sections, bns_file)

    # Combine
    all_sections = ipc_sections + bns_sections
    logger.info(f"Total sections loaded: {len(all_sections)}")

    return all_sections


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    corpus = build_corpus()
    print(f"✓ Built corpus with {len(corpus)} sections")
