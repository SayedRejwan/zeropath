# TryHackMe Room Catalog & Attack Knowledge Base

This catalog documents TryHackMe challenge rooms, attack chains, and techniques harvested from technical writeups and security articles for consumption by ZeroPath agents.

| Room Code | Title | Difficulty | Category | Key Tools | Attack Sequence |
|---|---|---|---|---|---|
| [`agentsudo`](agentsudo.yaml) | Agent Sudo | Easy | Linux | nmap, ffuf, hydra, john | Network_And_Web_Enumeration → Remote_Command_Injection → Sudo_Privilege_Abuse |
| [`allinone`](allinone.yaml) | All in One | Easy | Linux | nmap, ffuf, hydra, john | Network_And_Web_Enumeration → Remote_Command_Injection → Cron_Job_Hijack |
| [`baronsamedit`](baronsamedit.yaml) | Baron Samedit | Easy | Linux | nmap, nikto, john, metasploit | Network_And_Web_Enumeration → Remote_Command_Injection → SUID_Binary_Abuse |
| [`bountyhacker`](bountyhacker.yaml) | Bounty Hacker | Easy | Linux | nmap, hydra | Network_And_Web_Enumeration → Remote_Command_Injection → Sudo_Privilege_Abuse |
| [`chocolatefactory`](chocolatefactory.yaml) | Chocolate Factory | Easy | Linux | nmap, ffuf, hydra, john | Network_And_Web_Enumeration → Remote_Command_Injection → Sudo_Privilege_Abuse |
| [`active_directory_basics`](active_directory_basics.yaml) | Active Directory Basics | Easy | Walkthrough | - | Remote_Command_Injection → Privilege_Escalation |
| [`ad__basic_enumeration`](ad__basic_enumeration.yaml) | AD: Basic Enumeration | Easy | Walkthrough | nmap, smbclient, enum4linux, crackmapexec | Network_And_Web_Enumeration → Remote_Command_Injection → Privilege_Escalation |
| [`ai_security_threats`](ai_security_threats.yaml) | AI Security Threats | Easy | Walkthrough | - | Remote_Command_Injection → Privilege_Escalation |
| [`container_hardening`](container_hardening.yaml) | Container Hardening | Easy | Walkthrough | - | Network_And_Web_Enumeration → Remote_Command_Injection → SUID_Binary_Abuse |
| [`container_vulnerabilities`](container_vulnerabilities.yaml) | Container Vulnerabilities | Easy | Walkthrough | nmap, netcat, curl, wget | Network_And_Web_Enumeration → Remote_Command_Injection → Privilege_Escalation |
| [`cryptography_basics`](cryptography_basics.yaml) | Cryptography Basics | Easy | Walkthrough | - | Remote_Command_Injection → Privilege_Escalation |
| [`cyber_kill_chain`](cyber_kill_chain.yaml) | Cyber Kill Chain | Easy | Walkthrough | metasploit, responder | Network_And_Web_Enumeration → Remote_Command_Injection → Privilege_Escalation |
| [`diamond_model`](diamond_model.yaml) | Diamond Model | Easy | Walkthrough | metasploit | Network_And_Web_Enumeration → Remote_Command_Injection → Privilege_Escalation |
| [`hashing_basics`](hashing_basics.yaml) | Hashing Basics | Easy | Walkthrough | john, hashcat | Remote_Command_Injection → Privilege_Escalation |
| [`intro_to_containerisation`](intro_to_containerisation.yaml) | Intro to Containerisation | Easy | Walkthrough | - | Remote_Command_Injection → Privilege_Escalation |
| [`intro_to_cyber_threat_intel`](intro_to_cyber_threat_intel.yaml) | Intro to Cyber Threat Intel | Easy | Walkthrough | - | Network_And_Web_Enumeration → Remote_Command_Injection → Privilege_Escalation |
| [`intro_to_docker`](intro_to_docker.yaml) | Intro to Docker | Easy | Walkthrough | gobuster, curl | Network_And_Web_Enumeration → Remote_Command_Injection → Privilege_Escalation |
| [`intro_to_kubernetes`](intro_to_kubernetes.yaml) | Intro to Kubernetes | Easy | Walkthrough | - | Remote_Command_Injection → Privilege_Escalation |
| [`john_the_ripper__the_basics`](john_the_ripper__the_basics.yaml) | John the Ripper: The Basics | Easy | Walkthrough | john, curl, wget | Remote_Command_Injection → Privilege_Escalation |
| [`microservices_architectures`](microservices_architectures.yaml) | Microservices Architectures | Easy | Walkthrough | - | Remote_Command_Injection → Privilege_Escalation |
| [`prompt_engineering`](prompt_engineering.yaml) | Prompt Engineering | Easy | Walkthrough | - | Remote_Command_Injection → Privilege_Escalation |
| [`public_key_cryptography_basics`](public_key_cryptography_basics.yaml) | Public Key Cryptography Basics | Easy | Walkthrough | john | Remote_Command_Injection → Privilege_Escalation |
| [`pyramid_of_pain`](pyramid_of_pain.yaml) | Pyramid Of Pain | Easy | Walkthrough | responder, wireshark | Network_And_Web_Enumeration → Remote_Command_Injection → Privilege_Escalation |
| [`the_building_blocks_of_ai`](the_building_blocks_of_ai.yaml) | The Building Blocks of AI | Easy | Walkthrough | - | Remote_Command_Injection → Privilege_Escalation |
| [`threat_intelligence_tools`](threat_intelligence_tools.yaml) | Threat Intelligence Tools | Easy | Walkthrough | - | Remote_Command_Injection → Privilege_Escalation |
| [`trooper`](trooper.yaml) | Trooper | Easy | Walkthrough | - | Web_Vulnerability_Exploitation → Privilege_Escalation |
| [`unified_kill_chain`](unified_kill_chain.yaml) | Unified Kill Chain | Easy | Walkthrough | - | Network_And_Web_Enumeration → Remote_Command_Injection → Privilege_Escalation |
| [`virtualization_and_containers`](virtualization_and_containers.yaml) | Virtualization and Containers | Easy | Walkthrough | curl | Remote_Command_Injection → Privilege_Escalation |
| [`virtualization_basics`](virtualization_basics.yaml) | Virtualization Basics | Easy | Walkthrough | - | Remote_Command_Injection → Privilege_Escalation |
| [`yara`](yara.yaml) | Yara | Easy | Walkthrough | nc, curl, wget | Remote_Command_Injection → Cron_Job_Hijack |
| [`ai_forensics`](ai_forensics.yaml) | AI Forensics | Medium | Walkthrough | - | Network_And_Web_Enumeration → Remote_Command_Injection → Privilege_Escalation |
| [`ai_models___data`](ai_models___data.yaml) | AI Models & Data | Medium | Walkthrough | - | Remote_Command_Injection → Privilege_Escalation |
| [`atomic_red_team`](atomic_red_team.yaml) | Atomic Red Team | Medium | Walkthrough | metasploit, winpeas, curl | Network_And_Web_Enumeration → Remote_Command_Injection → Privilege_Escalation |
| [`basic_malware_re`](basic_malware_re.yaml) | Basic Malware RE | Medium | Walkthrough | - | Remote_Command_Injection → Privilege_Escalation |
| [`basic_static_analysis`](basic_static_analysis.yaml) | Basic Static Analysis | Medium | Walkthrough | - | Remote_Command_Injection → Privilege_Escalation |
| [`dll_hijacking`](dll_hijacking.yaml) | DLL HIJACKING | Medium | Walkthrough | john, wget | Remote_Command_Injection → Privilege_Escalation |
| [`elastic_stack__the_basics`](elastic_stack__the_basics.yaml) | Elastic Stack: The Basics | Medium | Walkthrough | - | Remote_Command_Injection → Privilege_Escalation |
| [`expediting_registry_analysis`](expediting_registry_analysis.yaml) | Expediting Registry Analysis | Medium | Walkthrough | responder | Remote_Command_Injection → Privilege_Escalation |
| [`intro_to_malware_analysis`](intro_to_malware_analysis.yaml) | Intro to Malware Analysis | Medium | Walkthrough | wireshark | Remote_Command_Injection → Privilege_Escalation |
| [`linux_privesc`](linux_privesc.yaml) | Linux PrivEsc | Medium | Walkthrough | nmap, john, metasploit, linpeas | Network_And_Web_Enumeration → Remote_Command_Injection → Sudo_Privilege_Abuse |
| [`linux_privesc_arena`](linux_privesc_arena.yaml) | network | Medium | Walkthrough | nmap, john, hashcat, linpeas | Network_And_Web_Enumeration → Remote_Command_Injection → Sudo_Privilege_Abuse |
| [`linux_privilege_escalation`](linux_privilege_escalation.yaml) | Linux Privilege Escalation | Medium | Walkthrough | nmap, john, linpeas, nc | Network_And_Web_Enumeration → Remote_Command_Injection → Sudo_Privilege_Abuse |
| [`llm_security`](llm_security.yaml) | LLM Security | Medium | Walkthrough | - | Network_And_Web_Enumeration → Remote_Command_Injection → Privilege_Escalation |
| [`logless_hunt`](logless_hunt.yaml) | Logless Hunt | Medium | Walkthrough | john, curl | Network_And_Web_Enumeration → Remote_Command_Injection → Privilege_Escalation |
| [`maldoc__static_analysis`](maldoc__static_analysis.yaml) | MalDoc: Static Analysis | Medium | Walkthrough | curl | Remote_Command_Injection → Privilege_Escalation |
| [`misp`](misp.yaml) | MISP | Medium | Walkthrough | - | Remote_Command_Injection → Privilege_Escalation |
| [`mitre`](mitre.yaml) | MITRE | Medium | Walkthrough | - | Network_And_Web_Enumeration → Remote_Command_Injection → Privilege_Escalation |
| [`opencti`](opencti.yaml) | OpenCTI | Medium | Walkthrough | bloodhound | Remote_Command_Injection → Privilege_Escalation |
| [`redline`](redline.yaml) | Redline | Medium | Walkthrough | responder | Network_And_Web_Enumeration → Remote_Command_Injection → Privilege_Escalation |
| [`securing_ai_systems`](securing_ai_systems.yaml) | Securing AI Systems | Medium | Walkthrough | - | Network_And_Web_Enumeration → Remote_Command_Injection → Privilege_Escalation |
| [`snort`](snort.yaml) | Snort | Medium | Walkthrough | wireshark | Remote_Command_Injection → Privilege_Escalation |
| [`splunk__exploring_spl`](splunk__exploring_spl.yaml) | Splunk: Exploring SPL | Medium | Walkthrough | john | Network_And_Web_Enumeration → Remote_Command_Injection → Privilege_Escalation |
| [`wazuh`](wazuh.yaml) | Wazuh | Medium | Walkthrough | netcat, curl | Remote_Command_Injection → Privilege_Escalation |
| [`windows_event_logs`](windows_event_logs.yaml) | Windows Event Logs | Medium | Walkthrough | - | Remote_Command_Injection → Privilege_Escalation |
| [`archangel`](archangel.yaml) | Archangel | Easy | Web | nmap, ffuf, metasploit, curl | Network_And_Web_Enumeration → Remote_Command_Injection → Cron_Job_Hijack |
| [`basic_pentesting`](basic_pentesting.yaml) | Basic Pentesting | Easy | Web | nmap, ffuf, hydra, john | Network_And_Web_Enumeration → Remote_Command_Injection → Privilege_Escalation |
| [`bolt`](bolt.yaml) | Bolt | Easy | Web | nmap, metasploit | Network_And_Web_Enumeration → Remote_Command_Injection → Privilege_Escalation |
| [`colddbox`](colddbox.yaml) | ColddBox: Easy | Easy | Web | nmap, ffuf, wpscan, metasploit | Network_And_Web_Enumeration → Remote_Command_Injection → SUID_Binary_Abuse |
| [`ignite`](ignite.yaml) | Ignite | Easy | Web | nmap, nc, wget | Network_And_Web_Enumeration → Remote_Command_Injection → Privilege_Escalation |
| [`inclusion`](inclusion.yaml) | Inclusion | Easy | Web | - | Remote_Command_Injection → Sudo_Privilege_Abuse |
| [`picklerick`](picklerick.yaml) | Pickle-Rick- | Easy | Web | nmap, dirsearch, netcat | Network_And_Web_Enumeration → Remote_Command_Injection → Privilege_Escalation |
| [`biohazard`](biohazard.yaml) | Biohazard | Medium | Web | nmap, binwalk | Network_And_Web_Enumeration → Remote_Command_Injection → Sudo_Privilege_Abuse |
| [`dailybugle`](dailybugle.yaml) | Daily Bugle | Medium | Web | john, sqlmap, metasploit, msfconsole | Remote_Command_Injection → Sudo_Privilege_Abuse |
| [`blue`](blue.yaml) | Blue | Easy | Windows | nmap, john, metasploit | Network_And_Web_Enumeration → Remote_Command_Injection → Privilege_Escalation |
| [`ice`](ice.yaml) | Ice | Easy | Windows | nmap, john, metasploit | Network_And_Web_Enumeration → Remote_Command_Injection → Windows_Token_Impersonation |
| [`introtowindowsir`](introtowindowsir.yaml) | THM: Introtowindowsir | Medium | Windows | powershell, wevtutil, reg, netstat | Artifact_And_Event_Log_Inspection → Persistence_Registry_Analysis |

## Usage in ZeroPath
Rooms documented here are loaded into `zeropath_local.db` and can be queried by:
- SQLite relational queries (e.g. `list_room_techniques(room_code)`)
- Graph attack-path queries (`kb.graph.shortest_path(src, dst)`)
