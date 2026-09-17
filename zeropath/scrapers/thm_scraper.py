from __future__ import annotations

import random
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

# User-Agent rotation pool adapted from F:\07_AUTOMATION_AGENTS\JOB ENGINE\nemu_engine\scanners\universal_scraper.py
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

COMMON_SECURITY_TOOLS = [
    "nmap", "gobuster", "ffuf", "dirbuster", "dirsearch", "nikto", "burpsuite",
    "hydra", "john", "hashcat", "sqlmap", "wpscan", "metasploit", "msfconsole",
    "linpeas", "winpeas", "nc", "netcat", "curl", "wget", "smbclient", "enum4linux",
    "crackmapexec", "responder", "impacket", "bloodhound", "wireshark", "binwalk"
]


@dataclass
class AttackStep:
    order: int
    phase: str  # recon, initial_access, privilege_escalation, post_exploitation
    technique: str
    tool: str = ""
    command: str = ""
    notes: str = ""


@dataclass
class THMRoomProfile:
    code: str
    title: str
    difficulty: str = "Easy"
    category: str = "Web"
    description: str = ""
    tags: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    attack_chain: list[AttackStep] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "title": self.title,
            "difficulty": self.difficulty,
            "category": self.category,
            "description": self.description,
            "tags": self.tags,
            "tools": self.tools,
            "attack_chain": [asdict(step) for step in self.attack_chain],
            "sources": self.sources,
        }


class THMScraper:
    """
    Scraper and extraction engine for TryHackMe room writeups, Medium articles,
    and security blogs, based on F:\07_AUTOMATION_AGENTS skills.
    """

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    def _random_headers(self) -> dict[str, str]:
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def fetch_url_content(self, url: str) -> str:
        """
        Fetch URL content using a multi-strategy approach:
        1. Jina Reader (https://r.jina.ai/{url}) - clean markdown extraction
        2. Direct HTTP GET with desktop User-Agent and BeautifulSoup cleaning
        """
        # Tier 1: Jina Reader for clean markdown extraction
        jina_url = f"https://r.jina.ai/{url}"
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                resp = client.get(jina_url)
                if resp.status_code == 200 and len(resp.text) > 300 and "PAGE NOT FOUND" not in resp.text:
                    return resp.text
        except Exception:
            pass

        # Tier 2: Direct HTTP GET fallback
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                resp = client.get(url, headers=self._random_headers())
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for tag in soup(["script", "style", "nav", "footer", "header"]):
                        tag.decompose()
                    return soup.get_text(separator="\n")
        except Exception as exc:
            return f"Fetch error: {exc}"

        return ""

    def parse_writeup_text(self, text: str, source_url: str = "", room_hint: str = "") -> THMRoomProfile:
        """
        Parse raw writeup text or markdown into a structured THMRoomProfile.
        """
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        # 1. Determine Title & Code
        title = ""
        code = ""

        # Check for title patterns like "TryHackMe - RoomName", "TryHackMe: RoomName Walkthrough"
        for line in lines[:30]:
            match = re.search(r"(?:tryhackme|thm)[\s\-–—:]+([a-zA-Z0-9_\-\s]+?)(?:writeup|walkthrough|\n|$)", line, re.IGNORECASE)
            if match:
                extracted = match.group(1).strip()
                if extracted and len(extracted) < 40:
                    title = extracted
                    break

        # Check for explicit "Name: RoomName" or "Room: RoomName" patterns
        for line in lines[:30]:
            name_match = re.search(r"^(?:name|room|challenge)[:\s]+([a-zA-Z0-9_\-\s]+?)(?:#|\n|$)", line, re.IGNORECASE)
            if name_match:
                extracted = name_match.group(1).strip()
                if extracted and len(extracted) < 40 and "tryhackme" not in extracted.lower():
                    title = extracted
                    break

        if not title and room_hint:
            title = room_hint
        elif not title:
            # Fallback to first major header
            for line in lines[:10]:
                cleaned = line.lstrip("#").strip()
                cleaned = re.sub(r"^Title:\s*", "", cleaned, flags=re.IGNORECASE).strip()
                if cleaned and len(cleaned) < 60:
                    title = cleaned
                    break

        # Clean title of common suffixes and prefixes
        title = re.sub(r"^(?:Title:\s*|TryHackMe\s*[-–—:]\s*)", "", title, flags=re.IGNORECASE).strip()
        title = re.sub(r"\s*[-–—|]\s*(?:write[- ]?up|walkthrough|tryhackme|rawsec|ctf).*", "", title, flags=re.IGNORECASE).strip()

        if not title:
            title = "Unknown THM Room"

        # Sanitize code / slug
        code = re.sub(r"[^a-zA-Z0-9_]", "_", title.lower().replace(" ", "_")).strip("_")
        code = re.sub(r"_+", "_", code)
        if not code:
            code = "thm_room_" + str(abs(hash(source_url)))[:6]

        # 2. Extract Difficulty
        difficulty = "Easy"
        diff_match = re.search(r"difficulty[:\s]+(easy|medium|hard|insane)", text, re.IGNORECASE)
        if diff_match:
            difficulty = diff_match.group(1).capitalize()
        else:
            for d in ["Insane", "Hard", "Medium", "Easy"]:
                if re.search(rf"\b{d}\b", text, re.IGNORECASE):
                    difficulty = d
                    break

        # 3. Extract Category
        category = "Web"
        cat_match = re.search(r"category[:\s]+([a-zA-Z\s]+)(?:\n|$)", text, re.IGNORECASE)
        if cat_match:
            raw_cat = cat_match.group(1).strip()
            for known in ["Active Directory", "Windows", "Linux", "Web", "Forensics", "Privilege Escalation", "Network", "Crypto"]:
                if re.search(rf"\b{re.escape(known)}\b", raw_cat, re.IGNORECASE):
                    category = known
                    break
        else:
            if re.search(r"\b(active directory|ad|kerberos|domain controller)\b", text, re.IGNORECASE):
                category = "Active Directory"
            elif re.search(r"\b(windows|smb|powershell|rdp)\b", text, re.IGNORECASE):
                category = "Windows"
            elif re.search(r"\b(forensics|memory dump|volatility|wireshark|pcap)\b", text, re.IGNORECASE):
                category = "Forensics"
            elif re.search(r"\b(linux|ssh|cron|bash)\b", text, re.IGNORECASE):
                category = "Linux"
            elif re.search(r"\b(privilege escalation|privesc|suid|sudo)\b", text, re.IGNORECASE):
                category = "Privilege Escalation"

        # 4. Extract Tools Used
        tools_detected: list[str] = []
        for tool in COMMON_SECURITY_TOOLS:
            if re.search(rf"\b{re.escape(tool)}\b", text, re.IGNORECASE):
                tools_detected.append(tool)

        # 5. Extract Attack Chain & Techniques
        steps: list[AttackStep] = []
        step_counter = 1

        # Check for Recon / Port Scanning
        recon_tools = [t for t in tools_detected if t in ["nmap", "gobuster", "ffuf", "dirb", "dirsearch", "nikto", "wpscan", "smbclient", "enum4linux"]]
        if recon_tools or re.search(r"nmap|port scan|recon|enumeration", text, re.IGNORECASE):
            steps.append(
                AttackStep(
                    order=step_counter,
                    phase="recon",
                    technique="Network_And_Web_Enumeration",
                    tool=", ".join(recon_tools) if recon_tools else "nmap",
                    notes="Discovered active ports, services, and accessible web paths or shares.",
                )
            )
            step_counter += 1

        # Check for Initial Access Techniques
        foothold_tech = "Web_Vulnerability_Exploitation"
        foothold_notes = "Gained initial foothold on target system."

        if re.search(r"command injection|rce", text, re.IGNORECASE):
            foothold_tech = "Remote_Command_Injection"
            foothold_notes = "Exploited unvalidated user input executing OS commands."
        elif re.search(r"sql injection|sqli", text, re.IGNORECASE):
            foothold_tech = "SQL_Injection"
            foothold_notes = "Extracted credentials or achieved code execution via SQL injection."
        elif re.search(r"lfi|local file inclusion", text, re.IGNORECASE):
            foothold_tech = "Local_File_Inclusion"
            foothold_notes = "Traversed server filesystem to read sensitive files/keys."
        elif re.search(r"brute force|hydra|default cred", text, re.IGNORECASE):
            foothold_tech = "Credential_Brute_Force"
            foothold_notes = "Cracked authentication or used default administrative credentials."
        elif re.search(r"eternalblue|ms17-010|samba", text, re.IGNORECASE):
            foothold_tech = "SMB_Vulnerability_Exploit"
            foothold_notes = "Exploited SMB service vulnerability for remote code execution."

        steps.append(
            AttackStep(
                order=step_counter,
                phase="initial_access",
                technique=foothold_tech,
                tool="burpsuite, custom_payload" if "burpsuite" in tools_detected else "custom_payload",
                notes=foothold_notes,
            )
        )
        step_counter += 1

        # Check for Privilege Escalation
        privesc_tech = "Privilege_Escalation"
        privesc_notes = "Escalated privileges to root or Administrator."

        if re.search(r"sudo -l|sudo abuse", text, re.IGNORECASE):
            privesc_tech = "Sudo_Privilege_Abuse"
            privesc_notes = "Leveraged misconfigured sudo permissions to spawn root shell."
        elif re.search(r"suid|find.*perm -4000", text, re.IGNORECASE):
            privesc_tech = "SUID_Binary_Abuse"
            privesc_notes = "Exploited custom or misconfigured SUID binary to escalate privilege."
        elif re.search(r"cron|crontab", text, re.IGNORECASE):
            privesc_tech = "Cron_Job_Hijack"
            privesc_notes = "Modified writable script or binary executed by scheduled root cron job."
        elif re.search(r"kernel exploit|dirtycow|overlayfs", text, re.IGNORECASE):
            privesc_tech = "Linux_Kernel_Exploitation"
            privesc_notes = "Compiled and ran local kernel exploit."
        elif re.search(r"seimpersonateprivilege|juicypotato|printspoofer", text, re.IGNORECASE):
            privesc_tech = "Windows_Token_Impersonation"
            privesc_notes = "Escalated from service account to SYSTEM using potato exploit."

        steps.append(
            AttackStep(
                order=step_counter,
                phase="privilege_escalation",
                technique=privesc_tech,
                tool="linpeas" if "linpeas" in tools_detected else ("winpeas" if "winpeas" in tools_detected else "bash"),
                notes=privesc_notes,
            )
        )

        # 6. Build Description & Tags
        desc_snippet = ""
        for line in lines[:8]:
            if len(line) > 40 and not line.startswith("#"):
                desc_snippet = line
                break
        if not desc_snippet:
            desc_snippet = f"TryHackMe challenge focusing on {category} with {difficulty} difficulty."

        tags = [category.lower(), difficulty.lower()]
        for t in tools_detected[:5]:
            if t not in tags:
                tags.append(t)

        return THMRoomProfile(
            code=code,
            title=title,
            difficulty=difficulty,
            category=category,
            description=desc_snippet,
            tags=tags,
            tools=tools_detected,
            attack_chain=steps,
            sources=[source_url] if source_url else [],
        )

    def scrape_and_parse(self, url: str, room_hint: str = "") -> THMRoomProfile:
        content = self.fetch_url_content(url)
        return self.parse_writeup_text(content, source_url=url, room_hint=room_hint)
