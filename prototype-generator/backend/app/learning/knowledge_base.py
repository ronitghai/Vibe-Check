"""
knowledge_base.py
------------------
This file is the AZ-900 "knowledge base" the pitch deck talks about. It is
intentionally a plain Python file with hand-typed content — NOT a database,
NOT a vector store, NOT scraped from Microsoft Learn. That's a deliberate
choice, not a shortcut we forgot to finish:

  - It's easy for a non-engineer teammate to open this file and add/edit a
    fact or a question without touching any other code.
  - It removes the #1 risk the deck itself calls out (AI hallucinating exam
    content) for the highest-stakes content in the whole app: the questions
    used to score a learner's mastery. Every question below was written by a
    person, not generated.
  - A real ingestion pipeline (scraping Microsoft Learn docs, embeddings,
    a vector database) is explicitly a "fast follow" in the deck's own
    roadmap table, not part of this first build.

HOW THIS FILE IS USED ELSEWHERE (so you know what breaks if you rename things):
  - `learning/service.py` imports DOMAINS, QUESTION_BANK, SNIPPETS, and
    get_snippet_for_topic(). It samples QUESTION_BANK for the diagnostic quiz
    and hands SNIPPETS to the LLM as "facts you must base your questions on"
    when generating a personalized practice game.
  - Every dict in QUESTION_BANK has a "topic" key that must exactly match a
    "topic" key in the matching domain's SNIPPETS list — that's how a missed
    diagnostic question gets paired with the right explanation to show the
    learner (see get_snippet_for_topic at the bottom of this file).

HOW TO ADD MORE CONTENT:
  1. Pick one of the 3 DOMAINS below (these must match the real AZ-900 exam
     objective domains — don't add a 4th without also updating the frontend,
     which assumes exactly 3 domains for its progress bars).
  2. Add a new dict to that domain's SNIPPETS list with a short, unique
     "topic" slug (lowercase_with_underscores) and a 1-3 sentence "snippet"
     that is a genuinely accurate Azure fact.
  3. Add one or more matching dicts to that domain's QUESTION_BANK list,
     reusing the SAME "topic" slug, with a "question", exactly 4 "choices",
     and the 0-indexed "answerIndex" of the correct choice.
"""

import random

# The 3 official AZ-900 exam objective domains. The frontend dashboard and
# progress bar assume there are exactly 3 of these — if you add or remove a
# domain here, you'll also need to touch the AZ-900 React components.
DOMAINS = [
    "Cloud Concepts",
    "Azure Architecture & Services",
    "Azure Management & Governance",
]

# SNIPPETS: the "ground truth" facts. Each domain is a list of
# {"topic": <slug>, "snippet": <1-3 sentence fact>}.
# These are shown to the learner as explanations when they miss a diagnostic
# question tied to that topic, AND fed to the LLM (as-is, verbatim) as the
# only allowed source material when it writes a personalized practice game
# for that domain — see generate_practice_game() in service.py.
SNIPPETS = {
    "Cloud Concepts": [
        {
            "topic": "shared_responsibility",
            "snippet": (
                "In the shared responsibility model, the cloud provider is responsible for the "
                "security OF the cloud (physical datacenters, host infrastructure, network), "
                "while the customer is always responsible for security IN the cloud — data, "
                "identities, and access management — no matter which service model is used."
            ),
        },
        {
            "topic": "capex_opex",
            "snippet": (
                "Cloud computing shifts spending from CapEx (a large upfront capital investment "
                "in hardware you own) to OpEx (paying for what you use as an ongoing operating "
                "expense), improving cost predictability and removing the need to over-provision."
            ),
        },
        {
            "topic": "economies_of_scale",
            "snippet": (
                "Cloud providers achieve economies of scale by buying and running computing "
                "resources at massive volume, which lowers the per-unit cost of infrastructure "
                "compared to any single company running its own datacenter."
            ),
        },
        {
            "topic": "service_models",
            "snippet": (
                "IaaS (Infrastructure as a Service) gives you the most control, provisioning raw "
                "VMs, networking, and storage while the provider manages the physical hardware. "
                "PaaS (Platform as a Service) manages the underlying infrastructure so you focus "
                "on code (e.g. Azure App Service). SaaS (Software as a Service) delivers a "
                "complete, ready-to-use application (e.g. Microsoft 365)."
            ),
        },
        {
            "topic": "scalability_elasticity",
            "snippet": (
                "Scalability is the ability to increase or decrease resources to match demand. "
                "Elasticity is doing that automatically, in real time, in response to load. High "
                "availability keeps an application running with minimal downtime, and fault "
                "tolerance keeps a system operational even when a component fails."
            ),
        },
        {
            "topic": "cloud_deployment_models",
            "snippet": (
                "Public cloud resources are owned and operated by a third-party provider (like "
                "Azure) and shared across customers. Private cloud resources are used exclusively "
                "by one business. Hybrid cloud combines both, often for compliance or legacy-"
                "system reasons."
            ),
        },
        {
            "topic": "consumption_based_model",
            "snippet": (
                "In the consumption-based model, you pay only for the resources you use, can "
                "stop paying when you no longer need them, and can dynamically scale usage up or "
                "down instead of pre-purchasing fixed capacity."
            ),
        },
        {
            # Added in the "10-question diagnostic" pass, for extra variety on retakes.
            "topic": "serverless_computing",
            "snippet": (
                "Serverless computing lets developers build applications without managing the "
                "underlying servers — the cloud provider automatically allocates and scales "
                "compute resources, and you're billed based on actual execution rather than "
                "reserved capacity."
            ),
        },
        {
            "topic": "scaling_types",
            "snippet": (
                "Vertical scaling (scaling up/down) changes the size of a single resource, like "
                "upgrading a VM to a larger size. Horizontal scaling (scaling out/in) adds or "
                "removes instances of a resource, such as adding more VMs behind a load balancer."
            ),
        },
        {
            "topic": "global_reach",
            "snippet": (
                "Cloud computing offers global reach — deploying applications close to users "
                "anywhere in the world in minutes — and agility, letting organizations quickly "
                "provision and de-provision resources as business needs change."
            ),
        },
    ],
    "Azure Architecture & Services": [
        {
            "topic": "regions_pairs",
            "snippet": (
                "An Azure region is a set of datacenters within a latency-defined perimeter. "
                "Region pairs are two regions in the same geography, at least 300 miles apart, "
                "used for disaster recovery and staggered platform updates."
            ),
        },
        {
            "topic": "availability_zones",
            "snippet": (
                "Availability Zones are physically separate datacenter groupings within an Azure "
                "region, each with independent power, cooling, and networking, used to protect "
                "applications from datacenter-level failures."
            ),
        },
        {
            "topic": "resource_groups",
            "snippet": (
                "A resource group is a logical container that holds related Azure resources "
                "sharing the same lifecycle. A subscription is a logical unit tied to billing and "
                "access management, and Management Groups can organize multiple subscriptions."
            ),
        },
        {
            "topic": "compute_services",
            "snippet": (
                "Azure Virtual Machines provide full-control IaaS compute. Azure Container "
                "Instances/AKS run containerized workloads. Azure App Service is fully managed "
                "PaaS for web apps. Azure Functions is serverless, event-driven compute billed "
                "per execution, with no servers to provision or manage."
            ),
        },
        {
            "topic": "networking",
            "snippet": (
                "A Virtual Network (VNet) is the fundamental building block for private networking "
                "in Azure. A VPN Gateway connects on-premises networks to Azure over an encrypted "
                "connection across the public internet. ExpressRoute extends an on-premises "
                "network into Azure through a private, dedicated connection that does not travel "
                "over the public internet."
            ),
        },
        {
            "topic": "storage_types",
            "snippet": (
                "Azure Blob Storage stores unstructured data like images and backups. Azure Disk "
                "Storage provides persistent, high-performance disks for VMs. Azure Files offers "
                "fully managed file shares accessible over the standard SMB protocol."
            ),
        },
        {
            "topic": "storage_redundancy",
            "snippet": (
                "LRS (Locally Redundant Storage) replicates data three times within a single "
                "datacenter. ZRS (Zone-Redundant Storage) replicates across availability zones. "
                "GRS (Geo-Redundant Storage) replicates to a secondary, paired region for "
                "protection against a regional outage."
            ),
        },
        {
            "topic": "azure_dns_traffic_manager",
            "snippet": (
                "Azure DNS hosts domain names and provides name resolution. Azure Traffic Manager "
                "is a DNS-based traffic load balancer that distributes traffic across Azure "
                "regions to the most appropriate endpoint based on routing method and health."
            ),
        },
        {
            "topic": "vm_scale_sets",
            "snippet": (
                "Virtual Machine Scale Sets let you create and manage a group of identical, "
                "load-balanced VMs that automatically increase or decrease in number in response "
                "to demand or a defined schedule."
            ),
        },
        {
            "topic": "hybrid_services",
            "snippet": (
                "Azure Arc extends Azure management to resources running outside Azure, including "
                "on-premises servers and other clouds. Azure Stack lets organizations run Azure "
                "services in their own datacenter for hybrid scenarios."
            ),
        },
    ],
    "Azure Management & Governance": [
        {
            "topic": "pricing_tools",
            "snippet": (
                "The Pricing Calculator estimates the cost of Azure resources before you deploy "
                "them. The Total Cost of Ownership (TCO) Calculator compares on-premises "
                "infrastructure costs to running the same workload on Azure."
            ),
        },
        {
            "topic": "policy_blueprints",
            "snippet": (
                "Azure Policy evaluates resources for compliance with organizational rules (e.g. "
                "'only allow a specific VM size') and can flag or block non-compliant resources. "
                "Azure Blueprints package policies, role assignments, and resource templates "
                "together to repeatably deploy compliant environments."
            ),
        },
        {
            "topic": "rbac_entra",
            "snippet": (
                "Azure Role-Based Access Control (RBAC) grants fine-grained access to Azure "
                "resources by assigning roles to users, groups, or applications at a specific "
                "scope. Microsoft Entra ID (formerly Azure Active Directory) is Microsoft's "
                "cloud-based identity and access management service."
            ),
        },
        {
            "topic": "resource_locks",
            "snippet": (
                "Resource locks (CanNotDelete or ReadOnly) prevent accidental deletion or "
                "modification of a critical resource, regardless of a user's RBAC permissions. "
                "Tags are name/value pairs used to organize resources for cost tracking and "
                "management."
            ),
        },
        {
            "topic": "advisor_monitor",
            "snippet": (
                "Azure Advisor analyzes your resource configuration and usage to give personalized "
                "recommendations on cost, security, reliability, and performance. Azure Service "
                "Health reports outages and planned maintenance affecting your resources. Azure "
                "Monitor collects and analyzes telemetry from Azure resources."
            ),
        },
        {
            "topic": "sla",
            "snippet": (
                "A Service Level Agreement (SLA) describes Microsoft's commitments for uptime and "
                "connectivity for an Azure service. A composite SLA is calculated when multiple "
                "services with different individual SLAs are combined in one solution."
            ),
        },
        {
            "topic": "management_tools",
            "snippet": (
                "The Azure Portal is the web-based GUI for managing resources. Azure CLI and Azure "
                "PowerShell are command-line tools for scripting management tasks. Azure Resource "
                "Manager (ARM) templates define infrastructure as code in JSON for repeatable "
                "deployments."
            ),
        },
        {
            "topic": "security_center_defender",
            "snippet": (
                "Microsoft Defender for Cloud (formerly Azure Security Center) provides unified "
                "security posture management and threat protection, continuously assessing "
                "resources and recommending ways to improve your security posture."
            ),
        },
        {
            "topic": "azure_backup_site_recovery",
            "snippet": (
                "Azure Backup provides simple, reliable backup for on-premises and cloud "
                "workloads. Azure Site Recovery orchestrates and automates disaster recovery of "
                "on-premises and Azure VMs to a secondary location."
            ),
        },
        {
            "topic": "compliance_trust",
            "snippet": (
                "Microsoft's Trust Center and compliance documentation explain how Azure meets "
                "regulatory and compliance requirements (like GDPR, ISO, and HIPAA), helping "
                "customers understand their obligations under the shared responsibility model."
            ),
        },
    ],
}

# QUESTION_BANK: the pre-authored diagnostic questions. Each domain is a list
# of {"topic", "question", "choices" (exactly 4), "answerIndex" (0-3)}.
# service.start_assessment() randomly samples ~10 of these, spread across all
# 3 domains, for every diagnostic — nothing here is generated by the LLM.
QUESTION_BANK = {
    "Cloud Concepts": [
        {
            "topic": "shared_responsibility",
            "question": (
                "In the shared responsibility model, who is always responsible for data "
                "classification and identity/access management, no matter which service model "
                "(IaaS, PaaS, or SaaS) is used?"
            ),
            "choices": ["The cloud provider", "The customer", "A third-party auditor", "No one — it's automated"],
            "answerIndex": 1,
        },
        {
            "topic": "capex_opex",
            "question": "Which term describes a large upfront investment in physical hardware, like purchasing on-premises servers?",
            "choices": ["OpEx", "CapEx", "Elastic spending", "Consumption-based cost"],
            "answerIndex": 1,
        },
        {
            "topic": "economies_of_scale",
            "question": "Why can cloud providers typically offer lower per-unit compute costs than a single company running its own datacenter?",
            "choices": ["Government subsidies", "Economies of scale from massive purchasing volume", "They use lower-quality hardware", "They don't pay for electricity"],
            "answerIndex": 1,
        },
        {
            "topic": "service_models",
            "question": "Which cloud service model gives you the most control over the operating system and installed software, while the provider still manages the physical hardware?",
            "choices": ["SaaS", "PaaS", "IaaS", "FaaS"],
            "answerIndex": 2,
        },
        {
            "topic": "scalability_elasticity",
            "question": "A system that automatically adds or removes compute resources in real time based on current demand is demonstrating which characteristic?",
            "choices": ["High availability", "Elasticity", "Fault tolerance", "Redundancy"],
            "answerIndex": 1,
        },
        {
            "topic": "cloud_deployment_models",
            "question": "A company keeps sensitive financial data in its own on-premises datacenter but runs its public website on Azure. Which deployment model is this?",
            "choices": ["Public cloud", "Private cloud", "Hybrid cloud", "Community cloud"],
            "answerIndex": 2,
        },
        {
            "topic": "consumption_based_model",
            "question": "What is a key benefit of the consumption-based pricing model in the cloud?",
            "choices": ["You pay for resources even when idle", "You pay only for what you use and can scale down to reduce cost", "It requires a 3-year upfront contract", "Pricing never changes based on usage"],
            "answerIndex": 1,
        },
        {
            "topic": "serverless_computing",
            "question": "In serverless computing, what determines how you are billed?",
            "choices": ["A fixed monthly server rental fee", "Actual code execution, not reserved server capacity", "The number of employees using the app", "A one-time hardware purchase"],
            "answerIndex": 1,
        },
        {
            "topic": "scaling_types",
            "question": "Adding more virtual machine instances behind a load balancer to handle increased traffic is an example of which scaling approach?",
            "choices": ["Vertical scaling", "Horizontal scaling", "Static scaling", "Manual-only scaling"],
            "answerIndex": 1,
        },
        {
            "topic": "global_reach",
            "question": "Which cloud benefit describes the ability to quickly deploy resources in datacenters around the world to be close to your users?",
            "choices": ["Global reach", "CapEx investment", "Vendor lock-in", "On-premises hosting"],
            "answerIndex": 0,
        },
    ],
    "Azure Architecture & Services": [
        {
            "topic": "regions_pairs",
            "question": "What is the minimum distance Microsoft targets between the two regions in an Azure region pair?",
            "choices": ["10 miles", "100 miles", "300 miles", "1000 miles"],
            "answerIndex": 2,
        },
        {
            "topic": "availability_zones",
            "question": "What is an Azure Availability Zone?",
            "choices": ["A separate Azure region entirely", "A physically separate datacenter within a region with independent power and networking", "A backup copy of data in another country", "A type of virtual network"],
            "answerIndex": 1,
        },
        {
            "topic": "resource_groups",
            "question": "What is a resource group in Azure?",
            "choices": ["A billing-only construct with no other purpose", "A logical container that holds related resources sharing the same lifecycle", "A physical rack of servers", "A type of Azure subscription"],
            "answerIndex": 1,
        },
        {
            "topic": "compute_services",
            "question": "Which Azure service is best suited for running code in response to events without provisioning or managing any servers?",
            "choices": ["Azure Virtual Machines", "Azure Functions", "Azure Container Instances", "Azure App Service"],
            "answerIndex": 1,
        },
        {
            "topic": "networking",
            "question": "Which Azure networking service provides a private, dedicated connection from an on-premises network to Azure that does not travel over the public internet?",
            "choices": ["VPN Gateway", "ExpressRoute", "Azure Load Balancer", "Azure Front Door"],
            "answerIndex": 1,
        },
        {
            "topic": "storage_types",
            "question": "Which Azure storage service is designed for storing unstructured data like images, videos, and backups?",
            "choices": ["Azure Disk Storage", "Azure Blob Storage", "Azure Files", "Azure Table Storage"],
            "answerIndex": 1,
        },
        {
            "topic": "storage_redundancy",
            "question": "Which storage redundancy option replicates your data to a secondary Azure region for protection against a regional outage?",
            "choices": ["LRS", "ZRS", "GRS", "None of these replicate regionally"],
            "answerIndex": 2,
        },
        {
            "topic": "azure_dns_traffic_manager",
            "question": "What does Azure Traffic Manager do?",
            "choices": ["Hosts virtual machines", "Distributes DNS-based traffic across Azure regions to the best endpoint", "Encrypts data at rest", "Manages billing alerts"],
            "answerIndex": 1,
        },
        {
            "topic": "vm_scale_sets",
            "question": "What is the purpose of Virtual Machine Scale Sets?",
            "choices": ["To permanently delete unused VMs", "To automatically manage a group of identical, load-balanced VMs that scale with demand", "To back up VM disks", "To assign RBAC roles to VMs"],
            "answerIndex": 1,
        },
        {
            "topic": "hybrid_services",
            "question": "Which Azure service extends Azure management capabilities to on-premises and multi-cloud resources?",
            "choices": ["Azure Arc", "Azure Functions", "Azure Front Door", "Azure Bastion"],
            "answerIndex": 0,
        },
    ],
    "Azure Management & Governance": [
        {
            "topic": "pricing_tools",
            "question": "Which Azure tool helps you estimate the cost of Azure resources before you deploy them?",
            "choices": ["Azure Advisor", "Pricing Calculator", "Azure Policy", "Cost Management + Billing"],
            "answerIndex": 1,
        },
        {
            "topic": "policy_blueprints",
            "question": "What does Azure Policy do?",
            "choices": ["Grants users permission to access resources", "Evaluates resources for compliance with organizational rules and can flag or block non-compliant ones", "Estimates monthly cloud spend", "Encrypts data at rest"],
            "answerIndex": 1,
        },
        {
            "topic": "rbac_entra",
            "question": "What does Azure RBAC (Role-Based Access Control) primarily manage?",
            "choices": ["Network bandwidth allocation", "Fine-grained access to Azure resources based on assigned roles", "Data backup schedules", "Virtual machine sizing"],
            "answerIndex": 1,
        },
        {
            "topic": "resource_locks",
            "question": "What is the purpose of a resource lock in Azure?",
            "choices": ["To encrypt a resource", "To prevent accidental deletion or modification of a critical resource", "To hide a resource from billing reports", "To restart a resource automatically"],
            "answerIndex": 1,
        },
        {
            "topic": "advisor_monitor",
            "question": "Which Azure service provides personalized recommendations to help optimize cost, security, reliability, and performance?",
            "choices": ["Azure Monitor", "Azure Service Health", "Azure Advisor", "Azure Policy"],
            "answerIndex": 2,
        },
        {
            "topic": "sla",
            "question": "What does an Azure Service Level Agreement (SLA) describe?",
            "choices": ["The programming languages a service supports", "Microsoft's commitments for uptime and connectivity of a service", "The physical location of a datacenter", "The price of a virtual machine"],
            "answerIndex": 1,
        },
        {
            "topic": "management_tools",
            "question": "Which of the following lets you define and deploy Azure infrastructure as code using JSON templates?",
            "choices": ["Azure Cloud Shell", "Azure Resource Manager (ARM) templates", "Azure Portal", "Azure CLI"],
            "answerIndex": 1,
        },
        {
            "topic": "security_center_defender",
            "question": "What does Microsoft Defender for Cloud primarily provide?",
            "choices": ["Physical datacenter cooling", "Unified security posture management and threat protection recommendations", "Virtual machine autoscaling", "DNS name resolution"],
            "answerIndex": 1,
        },
        {
            "topic": "azure_backup_site_recovery",
            "question": "Which Azure service orchestrates disaster recovery by replicating VMs to a secondary location?",
            "choices": ["Azure Backup", "Azure Site Recovery", "Azure Monitor", "Azure Policy"],
            "answerIndex": 1,
        },
        {
            "topic": "compliance_trust",
            "question": "Where can customers find information about how Azure meets regulatory requirements like GDPR and ISO standards?",
            "choices": ["The Azure Marketplace", "Microsoft's Trust Center and compliance documentation", "The Pricing Calculator", "Azure Resource Manager"],
            "answerIndex": 1,
        },
    ],
}


# ---------------------------------------------------------------------------
# Content for the other 5 template games (see service.py's
# generate_practice_content dispatcher, which routes to a generator per
# game_id). Two kinds of entry here:
#
#   - DOMAIN_ICON_THEMES: used AS-IS, no LLM call involved. memory_match's
#     "content" is just a themed icon set (its mechanic is flip-and-match
#     identical pairs, so there's no fact to test, only a theme to apply).
#
#   - FALLBACK_*: what a generator falls back to if its LLM call fails,
#     times out, or comes back malformed — the exact same safety net
#     QUESTION_BANK provides for the diagnostic. These are real, hand-
#     checked content, not placeholders — if a fallback fires, the learner
#     should not be able to tell the difference from the LLM path working.
# ---------------------------------------------------------------------------

DOMAIN_ICON_THEMES = {
    "Cloud Concepts": ["☁️", "🌐", "💳", "📈", "🔄", "⚖️", "🏗️", "🔓"],
    "Azure Architecture & Services": ["🏢", "🖥️", "🔌", "💾", "📡", "🗺️", "🧩", "🔗"],
    "Azure Management & Governance": ["🛡️", "🔑", "📋", "💰", "🔒", "📊", "🖇️", "✅"],
}

FALLBACK_CROSSWORD = {
    "Cloud Concepts": [
        {"word": "CAPEX", "clue": "Large upfront investment in hardware you own"},
        {"word": "ELASTICITY", "clue": "Automatically scaling resources in response to load"},
        {"word": "IAAS", "clue": "Service model giving you the most control over the OS"},
    ],
    "Azure Architecture & Services": [
        {"word": "REGION", "clue": "A set of Azure datacenters within a latency-defined perimeter"},
        {"word": "BLOB", "clue": "Azure storage service for unstructured data like images"},
        {"word": "EXPRESSROUTE", "clue": "Private connection to Azure that skips the public internet"},
    ],
    "Azure Management & Governance": [
        {"word": "POLICY", "clue": "Evaluates resources for compliance with organizational rules"},
        {"word": "RBAC", "clue": "Role-based access control, the acronym"},
        {"word": "ADVISOR", "clue": "Gives personalized cost, security, and performance recommendations"},
    ],
}

FALLBACK_MATCHING = {
    "Cloud Concepts": [
        {"left": "IaaS", "right": "You manage the OS and apps, provider manages the hardware"},
        {"left": "PaaS", "right": "Provider manages the platform, you just focus on code"},
        {"left": "SaaS", "right": "A complete, ready-to-use application"},
        {"left": "CapEx", "right": "Paying upfront for hardware you own"},
    ],
    "Azure Architecture & Services": [
        {"left": "Availability Zone", "right": "A physically separate datacenter within a region"},
        {"left": "VPN Gateway", "right": "Connects on-premises networks to Azure over the public internet"},
        {"left": "ExpressRoute", "right": "A private connection to Azure that avoids the public internet"},
        {"left": "Resource Group", "right": "A logical container for resources sharing one lifecycle"},
    ],
    "Azure Management & Governance": [
        {"left": "RBAC", "right": "Grants access to resources based on assigned roles"},
        {"left": "Resource Lock", "right": "Prevents accidental deletion of a critical resource"},
        {"left": "Azure Advisor", "right": "Gives personalized optimization recommendations"},
        {"left": "SLA", "right": "Microsoft's commitment for uptime and connectivity"},
    ],
}

FALLBACK_PHRASE = {
    "Cloud Concepts": {"phrase": "SHARED RESPONSIBILITY", "category": "Cloud Concepts"},
    "Azure Architecture & Services": {"phrase": "AVAILABILITY ZONES", "category": "Azure Architecture & Services"},
    "Azure Management & Governance": {"phrase": "ROLE BASED ACCESS", "category": "Azure Management & Governance"},
}


def get_snippet_for_topic(domain: str, topic: str) -> str | None:
    """
    Look up the human-readable explanation for one topic within one domain.

    Used by service.submit_assessment() to attach a real, accurate
    explanation to every diagnostic question the learner got wrong — this is
    what "AI Tutor — explain mistakes" from the deck's hero workflow actually
    means in this build: not a fresh LLM call per mistake (more hallucination
    risk, more latency), just looking up the fact that question was based on.
    """
    for entry in SNIPPETS.get(domain, []):
        if entry["topic"] == topic:
            return entry["snippet"]
    return None


def get_random_snippet(domain: str) -> str:
    """
    Pick one random fact for `domain` — used for tic_tac_toe's `factCard`
    (see service.py's tic_tac_toe branch of generate_practice_content).
    Tic-Tac-Toe has no config slot to test knowledge with, so instead of
    forcing a quiz shape onto it, it just shows one true, grounded fact
    before the match starts. No LLM call, so nothing to hallucinate.
    """
    return random.choice(SNIPPETS[domain])["snippet"]
