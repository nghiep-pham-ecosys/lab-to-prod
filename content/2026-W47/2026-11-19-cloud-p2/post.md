---
date: 2026-11-19
series: cloud-devops
part: 2
title: "Hybrid connectivity: Site-to-Site VPN or Direct Connect"
channels: [linkedin, facebook, telegram, x_manual]
short_publish_at: null
sources:
  - https://docs.aws.amazon.com/vpn/latest/s2svpn/vpn-limits.html
  - https://docs.aws.amazon.com/directconnect/latest/UserGuide/encryption-in-transit.html
  - https://docs.aws.amazon.com/directconnect/latest/UserGuide/dedicated_connection.html
  - https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNTunnels.html
image_alt: "Table comparing AWS Site-to-Site VPN (IPsec over the internet, up to 1.25 Gbps per standard tunnel) with Direct Connect (private line, dedicated ports from 1 to 400 Gbps, not encrypted by default)."
status: approved
card:
  layout: table
  theme: paper
  headline: "VPN or Direct Connect?"
  rows:
    - ["VPN", "IPsec over the internet. Up to 1.25 Gbps per standard tunnel."]
    - ["Direct Connect", "Private line, dedicated ports 1 to 400 Gbps. Not encrypted by default."]
    - ["Both", "Direct Connect for traffic, VPN as backup or on top."]
  lesson: "Private is not the same as encrypted."
---

## linkedin

1.25 Gbps. That is the ceiling of one standard AWS Site-to-Site VPN tunnel, and it settles more architecture questions than I expected.

I am studying for the AWS Solutions Architect Professional exam, and "VPN or Direct Connect" comes up in almost every hybrid scenario. I used to answer by feel. Now I use three questions.

How much traffic? A Site-to-Site VPN connection has two tunnels, each up to 1.25 Gbps as standard. A dedicated Direct Connect port comes in 1, 10, 100 or 400 Gbps.

How fast do you need it? A VPN is configuration: it runs over the internet connection you already have. Direct Connect is a physical cross connect in a colocation facility. AWS says provisioning the port alone can take up to 72 business hours, and then your provider still has to connect it.

Does it need encryption? This is the one that surprised me. A VPN is IPsec, so it is encrypted. Direct Connect is private, but the documentation is plain: it does not encrypt traffic in transit by default. If you need encryption there, you add MACsec or run a VPN over the Direct Connect link.

So the common answer is both: Direct Connect for steady, heavy traffic, and a VPN as the backup path or as the encryption layer on top.

The lesson: private is not the same as encrypted. Check which one the requirement actually asks for.

Part 2 of my Cloud & DevOps notes.

#AWS #CloudArchitecture #Networking #LearningInPublic

## x

1.25 Gbps: the ceiling of one standard AWS Site-to-Site VPN tunnel.

VPN: IPsec over the internet, quick to set up.
Direct Connect: private line, dedicated ports from 1 to 400 Gbps, but NOT encrypted by default.

Private is not the same as encrypted.

## facebook

How do you connect an office or data centre to AWS? There are two main ways.

A Site-to-Site VPN is an encrypted tunnel over the normal internet. It is quick to set up, and a standard tunnel carries up to 1.25 Gbps.

Direct Connect is a private physical line into AWS, with dedicated ports from 1 to 400 Gbps. It is steadier and much bigger, but it takes real installation work. And one detail surprised me: it is private, but it is not encrypted by default.

Many companies use both: the private line for heavy traffic and the VPN as a backup.

Private is not the same as encrypted.

Part 2 of my Cloud & DevOps notes.

## telegram

VPN or Direct Connect to reach AWS from your own network?

VPN: IPsec over the internet, up to 1.25 Gbps per standard tunnel, quick to set up.
Direct Connect: private line, dedicated ports from 1 to 400 Gbps, needs a physical cross connect, and is not encrypted by default.

Common answer: both. Direct Connect for traffic, VPN as backup or as encryption on top.

Private is not the same as encrypted.

Part 2 of my Cloud & DevOps notes.
