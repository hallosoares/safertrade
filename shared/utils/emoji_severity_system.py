#!/usr/bin/env python3
"""
emoji_severity_system.py - SaferTrade Emoji Severity System

Maps severity levels to appropriate emojis for consistent alert formatting.
"""

from enum import Enum
from typing import Dict


class SeverityLevel(Enum):
    """Enumeration for severity levels"""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


def get_severity_emoji(severity: str) -> str:
    """
    Map severity level to appropriate emoji.

    Args:
        severity: Severity level as string (case insensitive)

    Returns:
        Emoji corresponding to severity level
    """
    severity = severity.upper().strip()

    severity_emojis = {
        "CRITICAL": "🔴",  # exploit, hack, rug pull
        "HIGH": "🟠",  # suspicious activity, whale dump
        "MEDIUM": "🟡",  # unusual patterns, MEV
        "LOW": "🟢",  # informational
    }

    return severity_emojis.get(severity, "🔵")  # default to blue for unknown


def get_severity_description(severity: str) -> str:
    """
    Get description of what the severity level represents.

    Args:
        severity: Severity level as string (case insensitive)

    Returns:
        Description of what the severity level represents
    """
    severity = severity.upper().strip()

    descriptions = {
        "CRITICAL": "exploit, hack, rug pull",
        "HIGH": "suspicious activity, whale dump",
        "MEDIUM": "unusual patterns, MEV",
        "LOW": "informational",
    }

    return descriptions.get(severity, "unknown")


def format_with_severity_emoji(message: str, severity: str) -> str:
    """
    Format a message with appropriate severity emoji prefix.

    Args:
        message: The message to format
        severity: Severity level

    Returns:
        Formatted message with emoji prefix
    """
    emoji = get_severity_emoji(severity)
    return f"{emoji} {message}"


def get_all_severity_mappings() -> Dict[str, Dict[str, str]]:
    """
    Get all severity mappings for reference.

    Returns:
        Dictionary with all severity mappings
    """
    return {
        "CRITICAL": {"emoji": "🔴", "description": "exploit, hack, rug pull"},
        "HIGH": {"emoji": "🟠", "description": "suspicious activity, whale dump"},
        "MEDIUM": {"emoji": "🟡", "description": "unusual patterns, MEV"},
        "LOW": {"emoji": "🟢", "description": "informational"},
    }


# Example usage
if __name__ == "__main__":
    # Example usage of the functions
    print("Severity mappings:")
    for level, data in get_all_severity_mappings().items():
        print(f"{level}: {data['emoji']} - {data['description']}")

    print("\nFormatted messages:")
    print(format_with_severity_emoji("Major exploit detected!", "CRITICAL"))
    print(format_with_severity_emoji("Whale dump predicted", "HIGH"))
    print(format_with_severity_emoji("Unusual MEV activity", "MEDIUM"))
    print(format_with_severity_emoji("New pool launched", "LOW"))
