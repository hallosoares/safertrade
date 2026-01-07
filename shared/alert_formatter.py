#!/usr/bin/env python3
"""
alert_formatter.py - SaferTrade Professional Alert Formatting S

        # Create volatility warning title based on direction
        if direction == 'SELL':
            title = f"⚠️ VOLATILITY WARNING: ${amount_usd:,.2f} SELL by {whale_name}"
            impact_warning = "📉 Expect price pressure and potential dump"
            recommendation = "💡 Consider delaying buy orders or reducing position size"
        else:
            title = f"📊 WHALE ACTIVITY: ${amount_usd:,.2f} {direction} by {whale_name}"
            impact_warning = "📈 May indicate institutional accumulation"
            recommendation = "💡 Monitor for continued activity and price impact"rmats alerts from various engines into standardized, professional output
for consumption by notification systems, Discord, Telegram, etc.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class AlertType(Enum):
    WHALE_ALERT = "whale_alert"
    MEV_ALERT = "mev_alert"
    EXPLOIT_ALERT = "exploit_alert"
    BRIDGE_ARBITRAGE = "bridge_arbitrage"
    FLASH_LOAN_RISK = "flash_loan_risk"
    INSTITUTIONAL_FLOW = "institutional_flow"
    GENERAL = "general"


@dataclass
class AlertMessage:
    """Structured alert message with standardized fields"""

    alert_type: AlertType
    title: str
    description: str
    severity: str  # 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    timestamp: datetime
    chain: Optional[str] = None
    amount_usd: Optional[float] = None
    token: Optional[str] = None
    address: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None
    estimated_impact: Optional[float] = None


class AlertTier(Enum):
    """Enumeration for alert tiers"""

    FREE = "free"
    PREMIUM = "premium"


class AlertFormatter:
    """Professional alert formatting system for SaferTrade"""

    def __init__(self, free_tier_delay: int = 300):  # 300 seconds = 5 minutes
        self.logger = logging.getLogger(__name__)
        self.free_tier_delay = free_tier_delay  # Delay for free tier in seconds
        self.tier_delays = {
            AlertTier.FREE: self.free_tier_delay,
            AlertTier.PREMIUM: 0,  # No delay for premium tier
        }

    def _should_delay_alert(self, tier: AlertTier) -> bool:
        """Check if alert should be delayed based on tier"""
        return self.tier_delays.get(tier, self.free_tier_delay) > 0

    def _get_delay_duration(self, tier: AlertTier) -> int:
        """Get delay duration in seconds for the tier"""
        return self.tier_delays.get(tier, self.free_tier_delay)

    def format_whale_alert(
        self, whale_data: Dict[str, Any], tier: AlertTier = AlertTier.FREE
    ) -> AlertMessage:
        """Format whale tracker data into professional alert"""
        whale_name = whale_data.get("whale_name", "Unknown Whale")
        amount_usd = float(
            whale_data.get("amount_usd", 0)
        )  # Convert to float immediately
        direction = whale_data.get("direction", "UNKNOWN")
        token = whale_data.get("token", "UNKNOWN")
        exchange = whale_data.get("exchange", "Unknown")
        chain = whale_data.get("chain", "ethereum")
        risk_level = whale_data.get("risk_level", "MEDIUM")
        from_address = whale_data.get("from_address", "0x...")
        ml_dump_probability = float(whale_data.get("ml_dump_probability", 0))
        timestamp = int(
            float(whale_data.get("timestamp", int(datetime.now().timestamp())))
        )

        # Determine severity based on risk level and amount
        if risk_level == "CRITICAL" or amount_usd > 5000000:  # $5M+
            severity = "CRITICAL"
        elif risk_level == "HIGH" or amount_usd > 1000000:  # $1M+
            severity = "HIGH"
        elif risk_level == "MEDIUM" or amount_usd > 100000:  # $100k+
            severity = "MEDIUM"
        else:
            severity = "LOW"

        # Create volatility warning title based on direction
        if direction == "SELL":
            title = f"⚠️ VOLATILITY WARNING: ${amount_usd:,.2f} SELL by {whale_name}"
            impact_warning = "📉 Expect price pressure and potential dump"
            recommendation = "💡 Consider delaying buy orders or reducing position size"
        else:
            title = f"� WHALE ACTIVITY: ${amount_usd:,.2f} {direction} by {whale_name}"
            impact_warning = "📈 May indicate institutional accumulation"
            recommendation = "💡 Monitor for continued activity and price impact"

        # Create detailed description focusing on risk/impact
        amount_eth = float(whale_data.get("amount_eth", 0))

        description_parts = [
            "**Market Impact Warning**",
            impact_warning,
            f"• **Whale:** {whale_name}",
            f"• **Size:** ${amount_usd:,.2f} USD ({amount_eth:,.4f} {token})",
            f"• **Action:** {direction}",
            f"• **Exchange:** {exchange}",
            f"• **From:** {from_address[:12]}...",
            "",
            recommendation,
            "",
        ]

        # Add ML prediction if available - focus on risk warnings
        if ml_dump_probability > 0:
            if ml_dump_probability > 85:
                description_parts.append(
                    "🚨 **DUMP RISK: CRITICAL** - Avoid buying, consider selling"
                )
            elif ml_dump_probability > 70:
                description_parts.append(
                    "⚠️ **DUMP RISK: HIGH** - Exercise extreme caution"
                )
            elif ml_dump_probability > 50:
                description_parts.append(
                    "📊 **DUMP RISK: MODERATE** - Monitor closely before trading"
                )
            else:
                description_parts.append(
                    f"� **DUMP RISK: LOW** ({ml_dump_probability:.1f}%) - Normal trading caution"
                )

        # Add intent classification if available
        intent_classification = whale_data.get("intent_classification")
        if intent_classification:
            description_parts.append(f"• **Intent:** {intent_classification}")

        # Add behavioral pattern if available
        behavioral_pattern = whale_data.get("behavioral_pattern")
        if behavioral_pattern:
            description_parts.append(f"• **Pattern:** {behavioral_pattern}")

        description = "\n".join(description_parts)

        # Apply tier-specific formatting
        if tier == AlertTier.FREE:
            # FREE TIER: Basic info, 5-minute delay, limited details
            # Reduce amount of detail in the description
            basic_description_parts = [
                "**Whale Activity Detected**",
                f"• **Name:** {whale_name}",
                f"• **Amount:** ${amount_usd:,.2f} USD",
                f"• **Direction:** {direction}",
                f"• **Chain:** {chain.upper()}",
            ]
            # Only include ML prediction in free tier if it's high risk
            if ml_dump_probability > 70:
                basic_description_parts.append(
                    f"• **ML Dump Risk:** {ml_dump_probability:.1f}%"
                )

            description = "\n".join(basic_description_parts)

            # In free tier, reduce detailed information
            return AlertMessage(
                alert_type=AlertType.WHALE_ALERT,
                title=title,
                description=description,
                severity=severity,
                timestamp=datetime.fromtimestamp(timestamp),
                chain=chain,
                amount_usd=amount_usd,
                token=token,
                # In free tier, don't show full address
                address=from_address[:8] + "..." if from_address else None,
                # For free tier, limit additional data to essentials
                additional_data={
                    k: v
                    for k, v in whale_data.items()
                    if k
                    in [
                        "whale_name",
                        "amount_usd",
                        "direction",
                        "chain",
                        "timestamp",
                        "ml_dump_probability",
                    ]
                },
                confidence=whale_data.get("ml_confidence_score"),
                estimated_impact=whale_data.get("ml_estimated_impact"),
            )
        else:  # PREMIUM TIER
            # PREMIUM TIER: Full context, instant, trading opportunities
            return AlertMessage(
                alert_type=AlertType.WHALE_ALERT,
                title=title,
                description=description,
                severity=severity,
                timestamp=datetime.fromtimestamp(timestamp),
                chain=chain,
                amount_usd=amount_usd,
                token=token,
                address=from_address,
                additional_data=whale_data,
                confidence=whale_data.get("ml_confidence_score"),
                estimated_impact=whale_data.get("ml_estimated_impact"),
            )

    def format_mev_alert(
        self, mev_data: Dict[str, Any], tier: AlertTier = AlertTier.FREE
    ) -> AlertMessage:
        """Format MEV analyzer data into professional alert"""
        # Implementation for MEV alerts
        title = f"⚡ MEV OPPORTUNITY: ${mev_data.get('profit_usd', 0):,.2f}"

        if tier == AlertTier.FREE:
            # FREE TIER: Basic info, 5-minute delay, limited details
            description = (
                f"MEV opportunity detected\n"
                f"Profit: ${mev_data.get('profit_usd', 0):,.2f}\n"
                f"Chain: {mev_data.get('chain', 'ethereum')}"
            )
        else:
            # PREMIUM TIER: Full context, instant, trading opportunities
            description = (
                f"MEV opportunity detected on {mev_data.get('chain', 'ethereum')}\n"
                f"Profit: ${mev_data.get('profit_usd', 0):,.2f}\n"
                f"Type: {mev_data.get('mev_type', 'Unknown')}\n"
                f"Transaction: {mev_data.get('tx_hash', 'N/A')[:12]}... if available"
            )

        return AlertMessage(
            alert_type=AlertType.MEV_ALERT,
            title=title,
            description=description,
            severity="MEDIUM",
            timestamp=datetime.now(),
            chain=mev_data.get("chain"),
            amount_usd=mev_data.get("profit_usd"),
            additional_data=mev_data
            if tier == AlertTier.PREMIUM
            else {
                k: v
                for k, v in mev_data.items()
                if k in ["profit_usd", "chain", "timestamp"]
            },
        )

    def format_exploit_alert(
        self, exploit_data: Dict[str, Any], tier: str = "free"
    ) -> AlertMessage:
        """Format exploit monitor data into professional alert with tier-specific detail"""
        # Build description based on tier following the specified format requirements

        if tier == "premium":
            # Premium tier with more detailed information
            title = f"💎 SaferTrade PREMIUM Alert\n🔴🔔 Exploit: {exploit_data.get('exploit_type', 'Unknown')}"

            description = "DeFi exploit or vulnerability detected\n"
            description += f"🌐 Network: {exploit_data.get('chain', 'ethereum')}\n"

            # Add transaction info if available
            tx_hash = exploit_data.get("exploit_tx_hash", "")
            if tx_hash:
                description += f"🔗 Attack Tx: [Phalcon Explorer](https://phalcon.blocksec.com/tx/{exploit_data.get('chain', 'ethereum')}/{tx_hash})\n"

            # Add target protocol and TVL info
            protocol = exploit_data.get("protocol", "Unknown")
            description += f"🎯 Target: {protocol}\n"

            tvl_before = exploit_data.get("tvl_before_exploit", {}).get(
                protocol, "Unknown"
            )
            if tvl_before != "Unknown":
                description += f"🏦 TVL: ${tvl_before:,.2f}\n"

            estimated_loss = exploit_data.get("estimated_loss", 0)
            description += f"💰 Loss: ${estimated_loss:,.2f}\n"

            # Calculate percentage of TVL lost if TVL is known
            if tvl_before != "Unknown" and tvl_before > 0:
                loss_percentage = (estimated_loss / tvl_before) * 100
                description += f"📊 Impact: {loss_percentage:.1f}% of TVL\n"

            # Add affected protocols
            affected_protocols = self.detect_affected_protocols(exploit_data)
            if (
                affected_protocols and len(affected_protocols) > 1
            ):  # More than just the main protocol
                description += "🏛️ Other Protocols Involved:\n"
                for i, affected_protocol in enumerate(
                    [p for p in affected_protocols if p != protocol][:3]
                ):  # Limit to 3
                    # Get TVL for affected protocol if available
                    affected_tvl = exploit_data.get("tvl_before_exploit", {}).get(
                        affected_protocol, "Unknown"
                    )
                    if affected_tvl != "Unknown":
                        description += (
                            f"  • {affected_protocol} - TVL: ${affected_tvl:,.2f}\n"
                        )
                    else:
                        description += f"  • {affected_protocol}\n"

            # Add trading opportunities if available
            trading_opps = exploit_data.get("trading_opportunities", [])
            if trading_opps:
                description += "\n⚡ TRADING OPPORTUNITIES\n"
                for opp in trading_opps[:2]:  # Limit to 2 opportunities
                    token = opp.get("token", "N/A")
                    action = opp.get("action", "N/A")
                    description += f"Token: {token}\n"
                    description += f"Action: {action}\n"
                    description += f"Risk Level: {opp.get('risk_level', 'HIGH')}\n"
                    expected_move = opp.get("expected_movement", "Unknown")
                    if expected_move != "Unknown":
                        description += f"Expected Movement: {expected_move}\n"

            # Add explorer links
            description += "\n🔗 Etherscan | Phalcon | Tenderly | Dedaub"

        else:
            # Free tier with basic information
            title = f"⚠️ SaferTrade Alert - FREE\n🔴 Alert: {exploit_data.get('exploit_type', 'Unknown')}"

            description = "DeFi exploit or vulnerability detected\n"
            description += f"Protocol: {exploit_data.get('protocol', 'Unknown')}\n"

            # Detect affected protocols for free tier
            affected_protocols = self.detect_affected_protocols(exploit_data)
            if affected_protocols:
                description += f"Affected: {', '.join(affected_protocols[:5])}{'...' if len(affected_protocols) > 5 else ''}\n"  # Limit to 5

            description += (
                f"💰 Balance Change: ${exploit_data.get('estimated_loss', 0):,.2f}\n"
            )

            # Add basic explorer links
            description += "🔗 Etherscan | Phalcon | Tenderly | Dedaub"

        return AlertMessage(
            alert_type=AlertType.EXPLOIT_ALERT,
            title=title,
            description=description,
            severity="HIGH",
            timestamp=datetime.now(),
            amount_usd=exploit_data.get("estimated_loss"),
            additional_data=exploit_data,
        )

    def detect_affected_protocols(self, exploit_data: Dict[str, Any]) -> list:
        """
        Detect which protocols are affected by the exploit.

        Args:
            exploit_data: The exploit data to analyze

        Returns:
            List of affected protocol names
        """
        affected_protocols = []

        # Check if there's a specific protocol in the exploit data
        if exploit_data.get("protocol"):
            affected_protocols.append(exploit_data["protocol"])

        # If transaction hash is available, try to analyze it for affected protocols
        tx_hash = exploit_data.get("exploit_tx_hash", "")
        if tx_hash:
            # In a real implementation, this would connect to blockchain analytics
            # to determine all protocols affected by the transaction
            pass

        # Check for affected addresses that might correspond to known protocols
        affected_addresses = exploit_data.get("affected_addresses", [])
        for address in affected_addresses:
            protocol_name = self._match_address_to_protocol(address)
            if protocol_name and protocol_name not in affected_protocols:
                affected_protocols.append(protocol_name)

        # Check for correlated protocols (if the exploit might affect related protocols)
        base_protocol = exploit_data.get("protocol", "")
        if base_protocol:
            correlated_protocols = self._find_correlated_protocols(base_protocol)
            for protocol in correlated_protocols:
                if protocol not in affected_protocols:
                    affected_protocols.append(protocol)

        return affected_protocols

    def _match_address_to_protocol(self, address: str) -> str:
        """
        Match an address to a known protocol name.

        Args:
            address: The blockchain address to check

        Returns:
            Protocol name if found, otherwise empty string
        """
        # In a real implementation, this would look up the address in a database
        # of known protocol addresses

        # Example mapping - in reality this would come from a comprehensive database
        protocol_addresses = {
            # These would be actual protocol contract addresses
            # '0x1f9840a85d5af5bf1d1762f925bdaddc4201f984': 'Uniswap',
            # '0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9': 'Aave',
        }

        return protocol_addresses.get(address.lower(), "")

    def _find_correlated_protocols(self, base_protocol: str) -> list:
        """
        Find protocols that might be affected by an exploit in the base protocol.

        Args:
            base_protocol: The main protocol where the exploit occurred

        Returns:
            List of potentially affected protocol names
        """
        # Define protocol relationships - in reality this would be more comprehensive
        protocol_correlations = {
            "Uniswap": ["SushiSwap", "PancakeSwap", "Curve"],
            "Aave": ["Compound", "MakerDAO", "Liquity"],
            "Compound": ["Aave", "MakerDAO", "Rari Capital"],
            "Curve": ["Balancer", "Uniswap", "SushiSwap"],
            "MakerDAO": ["Aave", "Compound", "Liquity"],
            "SushiSwap": ["Uniswap", "Curve", "PancakeSwap"],
        }

        return protocol_correlations.get(base_protocol, [])

    def generate_etherscan_link(self, hash_value: str, chain: str = "ethereum") -> str:
        """Generate Etherscan link for a given hash on the specified chain."""
        chain_links = {
            "ethereum": f"https://etherscan.io/tx/{hash_value}",
            "bsc": f"https://bscscan.com/tx/{hash_value}",
            "polygon": f"https://polygonscan.com/tx/{hash_value}",
            "arbitrum": f"https://arbiscan.io/tx/{hash_value}",
            "optimism": f"https://optimistic.etherscan.io/tx/{hash_value}",
            "base": f"https://basescan.org/tx/{hash_value}",
            "avalanche": f"https://snowtrace.io/tx/{hash_value}",
            "fantom": f"https://ftmscan.com/tx/{hash_value}",
        }
        return chain_links.get(chain.lower(), f"https://etherscan.io/tx/{hash_value}")

    def generate_phalcon_link(self, hash_value: str, chain: str = "ethereum") -> str:
        """Generate Phalcon link for a given hash on the specified chain."""
        return f"https://phalcon.blocksec.com/tx/{chain}/{hash_value}"

    def generate_tenderly_link(self, hash_value: str, chain: str = "ethereum") -> str:
        """Generate Tenderly link for a given hash on the specified chain."""
        return f"https://dashboard.tenderly.co/tx/{chain}/{hash_value}"

    def generate_dedaub_link(self, hash_value: str, chain: str = "ethereum") -> str:
        """Generate Dedaub link for a given hash on the specified chain."""
        return f"https://phalcon.xyz/tx/{chain}/{hash_value}"

    def generate_debank_link(self, address: str) -> str:
        """Generate Debank link for a given address."""
        return f"https://debank.com/profile/{address}"

    def generate_defillama_link(self, protocol: str) -> str:
        """Generate DefiLlama link for a given protocol."""
        return f"https://defillama.com/protocol/{protocol.lower().replace(' ', '-')}"

    def get_severity_emoji(self, severity: str) -> str:
        """
        Map severity levels to emojis.

        Args:
            severity: Severity level ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')

        Returns:
            Corresponding emoji
        """
        emoji_map = {
            "CRITICAL": "🔴",  # exploit, hack, rug pull
            "HIGH": "🟠",  # suspicious activity, whale dump
            "MEDIUM": "🟡",  # unusual patterns, MEV
            "LOW": "🟢",  # informational
        }
        return emoji_map.get(severity.upper(), "🟢")  # Default to green if unknown

    def format_bridge_alert(
        self, bridge_data: Dict[str, Any], tier: str = "free"
    ) -> AlertMessage:
        """Format bridge alert data into professional alert with tier-specific detail"""
        title = f"🌉 BRIDGE ARBITRAGE: ${bridge_data.get('profit_usd', 0):,.2f}"

        # Build description based on tier
        if tier == "premium":
            # Premium tier includes more detailed information following the specified format
            description = "Cross-chain bridge arbitrage opportunity\n"
            description += f"Chains: {bridge_data.get('from_chain', 'N/A')} -> {bridge_data.get('to_chain', 'N/A')}\n"
            description += f"Profit: ${bridge_data.get('profit_usd', 0):,.2f}\n"
            description += f"Token: {bridge_data.get('token', 'N/A')}\n"

            # Add premium-specific information
            route_details = bridge_data.get("route_details", "")
            if route_details:
                description += f"Route: {route_details}\n"

            risk_level = bridge_data.get("risk_level", "MEDIUM")
            description += f"Risk Level: {risk_level}\n"

            # Add potential market impact
            market_impact = bridge_data.get("market_impact", "Unknown")
            if market_impact != "Unknown":
                description += f"Market Impact: {market_impact}\n"

            # Add potential trading opportunities if applicable
            trading_opps = bridge_data.get("trading_opportunities", [])
            if trading_opps:
                description += "\n⚡ TRADING OPPORTUNITIES\n"
                for opp in trading_opps:
                    description += f"Token: {opp.get('token', 'N/A')}\n"
                    description += f"Action: {opp.get('action', 'N/A')}\n"
                    description += f"Risk Level: {opp.get('risk_level', 'MEDIUM')}\n"
                    expected_move = opp.get("expected_movement", "Unknown")
                    if expected_move != "Unknown":
                        description += f"Expected Movement: {expected_move}\n"
        else:
            # Free tier includes basic information following the specified format
            description = "Cross-chain bridge arbitrage opportunity\n"
            description += f"Chains: {bridge_data.get('from_chain', 'N/A')} -> {bridge_data.get('to_chain', 'N/A')}\n"
            description += f"Profit: ${bridge_data.get('profit_usd', 0):,.2f}\n"
            description += f"Token: {bridge_data.get('token', 'N/A')}"

        return AlertMessage(
            alert_type=AlertType.BRIDGE_ARBITRAGE,
            title=title,
            description=description,
            severity="MEDIUM",
            timestamp=datetime.now(),
            amount_usd=bridge_data.get("profit_usd"),
            additional_data=bridge_data,
        )

    # Backwards compatibility
    def format_bridge_arbitrage_alert(
        self, arbitrage_data: Dict[str, Any], tier: str = "free"
    ) -> AlertMessage:
        """Deprecated: Use format_bridge_alert instead"""
        return self.format_bridge_alert(arbitrage_data, tier)

    def format_flash_loan_alert(
        self, flashloan_data: Dict[str, Any], tier: str = "free"
    ) -> AlertMessage:
        """Format flash loan risk data into professional alert with tier-specific detail"""
        # Build description based on tier following the specified format requirements

        if tier == "premium":
            # Premium tier with more detailed information
            title = f"💎 SaferTrade PREMIUM Alert\n💳 FLASH LOAN RISK: {flashloan_data.get('risk_type', 'Unknown')}"

            description = "Flash loan attack vector detected\n"
            description += f"Protocol: {flashloan_data.get('protocol', 'Unknown')}\n"
            description += f"Risk Level: {flashloan_data.get('risk_level', 'MEDIUM')}\n"

            # Add more detailed information for premium tier
            amount = flashloan_data.get("amount_usd", 0)
            if amount > 0:
                description += f"Amount: ${amount:,.2f}\n"

            # Add transaction details if available
            tx_hash = flashloan_data.get("tx_hash", "")
            if tx_hash:
                description += f"Transaction: {tx_hash[:12]}...\n"

            # Add potential impact
            potential_impact = flashloan_data.get("potential_impact", "Unknown")
            if potential_impact != "Unknown":
                description += f"Potential Impact: {potential_impact}\n"

            # Add affected tokens if available
            affected_tokens = flashloan_data.get("affected_tokens", [])
            if affected_tokens:
                description += f"Affected Tokens: {', '.join(affected_tokens[:5])}{'...' if len(affected_tokens) > 5 else ''}\n"

            # Add trading opportunities if available
            trading_opps = flashloan_data.get("trading_opportunities", [])
            if trading_opps:
                description += "\n⚡ TRADING OPPORTUNITIES\n"
                for opp in trading_opps[:2]:  # Limit to 2 opportunities
                    description += f"Token: {opp.get('token', 'N/A')}\n"
                    description += f"Action: {opp.get('action', 'N/A')}\n"
                    description += f"Risk Level: {opp.get('risk_level', 'HIGH')}\n"
                    expected_move = opp.get("expected_movement", "Unknown")
                    if expected_move != "Unknown":
                        description += f"Expected Movement: {expected_move}\n"

            # Add explorer links
            description += "\n🔗 Etherscan | Phalcon | Tenderly | Dedaub"

        else:
            # Free tier with basic information
            title = f"⚠️ SaferTrade Alert - FREE\n💳 FLASH LOAN RISK: {flashloan_data.get('risk_type', 'Unknown')}"

            description = "Flash loan attack vector detected\n"
            description += f"Protocol: {flashloan_data.get('protocol', 'Unknown')}\n"
            description += f"Risk Level: {flashloan_data.get('risk_level', 'MEDIUM')}"

        return AlertMessage(
            alert_type=AlertType.FLASH_LOAN_RISK,
            title=title,
            description=description,
            severity=flashloan_data.get("risk_level", "MEDIUM").upper(),
            timestamp=datetime.now(),
            additional_data=flashloan_data,
        )

    def format_institutional_flow_alert(
        self, flow_data: Dict[str, Any], tier: str = "free"
    ) -> AlertMessage:
        """Format institutional flow data into professional alert with tier-specific detail"""
        # Build description based on tier following the specified format requirements

        if tier == "premium":
            # Premium tier with more detailed information
            title = f"💎 SaferTrade PREMIUM Alert\n🏢 INSTITUTIONAL FLOW: ${flow_data.get('amount_usd', 0):,.2f}"

            description = "Institutional accumulation/distribution detected\n"
            description += f"Entity: {flow_data.get('institution_name', 'Unknown')}\n"
            description += f"Amount: ${flow_data.get('amount_usd', 0):,.2f}\n"
            description += f"Direction: {flow_data.get('direction', 'Unknown')}\n"
            description += f"Chain: {flow_data.get('chain', 'ethereum')}\n"

            # Add more detailed information for premium tier
            risk_level = flow_data.get("risk_level", "MEDIUM")
            description += f"Risk Level: {risk_level}\n"

            # Add market impact if available
            market_impact = flow_data.get("market_impact", "Unknown")
            if market_impact != "Unknown":
                description += f"Market Impact: {market_impact}\n"

            # Add affected tokens if available
            affected_tokens = flow_data.get("affected_tokens", [])
            if affected_tokens:
                description += f"Affected Tokens: {', '.join(affected_tokens[:5])}{'...' if len(affected_tokens) > 5 else ''}\n"

            # Add trading opportunities if available
            trading_opps = flow_data.get("trading_opportunities", [])
            if trading_opps:
                description += "\n⚡ TRADING OPPORTUNITIES\n"
                for opp in trading_opps[:2]:  # Limit to 2 opportunities
                    description += f"Token: {opp.get('token', 'N/A')}\n"
                    description += f"Action: {opp.get('action', 'N/A')}\n"
                    description += f"Risk Level: {opp.get('risk_level', 'HIGH')}\n"
                    expected_move = opp.get("expected_movement", "Unknown")
                    if expected_move != "Unknown":
                        description += f"Expected Movement: {expected_move}\n"

            # Add explorer links
            description += "\n🔗 Etherscan | Phalcon | Tenderly | Dedaub"

        else:
            # Free tier with basic information
            title = f"⚠️ SaferTrade Alert - FREE\n🏢 INSTITUTIONAL FLOW: ${flow_data.get('amount_usd', 0):,.2f}"

            description = "Institutional accumulation/distribution detected\n"
            description += f"Entity: {flow_data.get('institution_name', 'Unknown')}\n"
            description += f"Amount: ${flow_data.get('amount_usd', 0):,.2f}\n"
            description += f"Direction: {flow_data.get('direction', 'Unknown')}"

        return AlertMessage(
            alert_type=AlertType.INSTITUTIONAL_FLOW,
            title=title,
            description=description,
            severity="MEDIUM",
            timestamp=datetime.now(),
            amount_usd=flow_data.get("amount_usd"),
            additional_data=flow_data,
        )

    def format_general_alert(self, alert_data: Dict[str, Any]) -> AlertMessage:
        """Format general alert data into professional alert"""
        title = alert_data.get("title", "General Alert")
        description = alert_data.get("description", "No description provided")
        severity = alert_data.get("severity", "MEDIUM")

        return AlertMessage(
            alert_type=AlertType.GENERAL,
            title=title,
            description=description,
            severity=severity.upper(),
            timestamp=datetime.now(),
            additional_data=alert_data,
        )

    def format_alert(
        self,
        alert_type: AlertType,
        data: Dict[str, Any],
        tier: AlertTier = AlertTier.FREE,
    ) -> AlertMessage:
        """Format alert based on type"""
        formatter_map = {
            AlertType.WHALE_ALERT: self.format_whale_alert,
            AlertType.MEV_ALERT: self.format_mev_alert,
            AlertType.EXPLOIT_ALERT: self.format_exploit_alert,
            AlertType.BRIDGE_ARBITRAGE: self.format_bridge_arbitrage_alert,
            AlertType.FLASH_LOAN_RISK: self.format_flash_loan_alert,
            AlertType.INSTITUTIONAL_FLOW: self.format_institutional_flow_alert,
        }

        formatter = formatter_map.get(alert_type, self.format_general_alert)
        return formatter(data, tier)

    def delay_for_tier(self, tier: AlertTier):
        """Delay execution based on user tier (for free tier alerts only)"""
        import os
        import time

        delay_seconds = self._get_delay_duration(tier)
        # Bypass mechanism for internal engine verification / ops
        if os.getenv("SAFERTRADE_ALERT_DELAY_BYPASS", "0") == "1":
            if delay_seconds > 0:
                self.logger.debug(
                    f"Bypassing free tier alert delay ({delay_seconds}s) due to SAFERTRADE_ALERT_DELAY_BYPASS=1"
                )
            return
        if delay_seconds > 0:
            self.logger.info(f"Delaying alert for free tier by {delay_seconds} seconds")
            time.sleep(delay_seconds)

    def format_for_discord(
        self, alert_message: AlertMessage, tier: AlertTier = AlertTier.FREE
    ) -> Dict[str, Any]:
        """Format alert message for Discord webhook with tier-specific behavior"""
        if tier == AlertTier.FREE:
            self.delay_for_tier(tier)  # Apply delay for free tier

        color_map = {
            "CRITICAL": 0xFF0000,  # Red
            "HIGH": 0xFFA500,  # Orange
            "MEDIUM": 0xFFFF00,  # Yellow
            "LOW": 0x00FF00,  # Green
        }

        embed = {
            "title": alert_message.title,
            "description": alert_message.description,
            "color": color_map.get(alert_message.severity, 0x808080),  # Gray default
            "timestamp": alert_message.timestamp.isoformat(),
            "fields": [],
        }

        # Add additional fields based on alert type and data
        if alert_message.chain:
            embed["fields"].append(
                {"name": "Chain", "value": alert_message.chain.upper(), "inline": True}
            )

        if alert_message.token:
            embed["fields"].append(
                {"name": "Token", "value": alert_message.token, "inline": True}
            )

        if alert_message.amount_usd is not None:
            embed["fields"].append(
                {
                    "name": "Amount (USD)",
                    "value": f"${alert_message.amount_usd:,.2f}",
                    "inline": True,
                }
            )

        # Add confidence and impact if available
        if alert_message.confidence is not None:
            embed["fields"].append(
                {
                    "name": "Confidence",
                    "value": f"{alert_message.confidence:.1%}",
                    "inline": True,
                }
            )

        if alert_message.estimated_impact is not None:
            embed["fields"].append(
                {
                    "name": "Estimated Impact",
                    "value": f"{alert_message.estimated_impact:.2f}%",
                    "inline": True,
                }
            )

        if alert_message.address:
            embed["fields"].append(
                {
                    "name": "Address",
                    "value": f"`{alert_message.address[:12]}...`",
                    "inline": False,
                }
            )

        return {
            "embeds": [embed],
            "username": "SaferTrade Alert System",
            "avatar_url": "https://safertrade.app/alert-icon.png",  # Placeholder
        }

    def format_for_telegram(
        self, alert_message: AlertMessage, tier: AlertTier = AlertTier.FREE
    ) -> str:
        """Format alert message for Telegram with tier-specific behavior"""
        if tier == AlertTier.FREE:
            self.delay_for_tier(tier)  # Apply delay for free tier

        header_emojis = {"CRITICAL": "🚨", "HIGH": "⚠️", "MEDIUM": "📊", "LOW": "ℹ️"}

        header = f"{header_emojis.get(alert_message.severity, '🔔')} **{alert_message.title}**\n\n"
        body = f"{alert_message.description}\n\n"

        footer_parts = []
        if alert_message.chain:
            footer_parts.append(f"🌐 *Chain:* `{alert_message.chain.upper()}`")

        if alert_message.token:
            footer_parts.append(f"🪙 *Token:* `{alert_message.token}`")

        if alert_message.amount_usd is not None:
            footer_parts.append(f"💰 *Amount:* `${alert_message.amount_usd:,.2f}`")

        if alert_message.confidence is not None:
            footer_parts.append(f"🎯 *Confidence:* `{alert_message.confidence:.1%}`")

        if alert_message.estimated_impact is not None:
            footer_parts.append(f"📉 *Impact:* `{alert_message.estimated_impact:.2f}%`")

        if alert_message.address:
            footer_parts.append(f"📍 *Address:* `{alert_message.address[:12]}...`")

        footer_parts.append(
            f"🕐 *Time:* `{alert_message.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}`"
        )

        footer = "\n".join(footer_parts)

        return f"{header}{body}{footer}"

    def format_for_console(
        self, alert_message: AlertMessage, tier: AlertTier = AlertTier.FREE
    ) -> str:
        """Format alert message for console logging with tier-specific behavior"""
        if tier == AlertTier.FREE:
            self.delay_for_tier(tier)  # Apply delay for free tier

        severity_colors = {
            "CRITICAL": "\033[91m",  # Red
            "HIGH": "\033[93m",  # Yellow
            "MEDIUM": "\033[94m",  # Blue
            "LOW": "\033[92m",  # Green
        }
        reset_color = "\033[0m"

        color = severity_colors.get(alert_message.severity, "")

        formatted = (
            f"{color}[{alert_message.severity}] {alert_message.title}{reset_color}\n"
        )
        formatted += f"Description: {alert_message.description}\n"

        if alert_message.chain:
            formatted += f"Chain: {alert_message.chain.upper()}\n"

        if alert_message.token:
            formatted += f"Token: {alert_message.token}\n"

        if alert_message.amount_usd is not None:
            formatted += f"Amount (USD): ${alert_message.amount_usd:,.2f}\n"

        if alert_message.confidence is not None:
            formatted += f"Confidence: {alert_message.confidence:.1%}\n"

        if alert_message.estimated_impact is not None:
            formatted += f"Estimated Impact: {alert_message.estimated_impact:.2f}%\n"

        if alert_message.address:
            formatted += f"Address: {alert_message.address[:12]}...\n"

        formatted += f"Timestamp: {alert_message.timestamp}\n"

        return formatted


def format_and_publish_exploit_alert(exploit_data: Dict[str, Any], tier: str = "free"):
    """
    Wrapper function to format and publish exploit alerts through the standardized system.
    This function is used by engines to publish alerts using the new tiered alert system.

    Args:
        exploit_data: Raw exploit data from detection engines
        tier: Alert tier ('free', 'premium', 'critical')
    """
    try:
        import logging

        from .alert_formatter import AlertFormatter

        logger = logging.getLogger(__name__)

        # Create an alert formatter instance
        formatter = AlertFormatter()

        # Format the exploit data into a standardized AlertMessage
        alert_message = formatter.format_exploit_alert(exploit_data, tier)

        # Determine severity for routing
        severity = exploit_data.get("severity", "MEDIUM")

        # Import and use the new tiered alert systems
        try:
            from .discord_alerts import send_discord_alert

            send_discord_alert(alert_message, tier, severity)
            logger.info(f"Exploit alert sent to Discord for tier {tier}")
        except ImportError:
            logger.warning("Discord alerts module not available")

        try:
            from .telegram_alerts import send_telegram_alert

            send_telegram_alert(alert_message, tier, severity)
            logger.info(f"Exploit alert sent to Telegram for tier {tier}")
        except ImportError:
            logger.warning("Telegram alerts module not available")

        # Publish to WebSocket system if available
        try:
            from api.websockets.alerts import publish_alert

            # Map to appropriate WebSocket alert type
            alert_type_map = {
                "exploit_alert": "exploit_alert_triggered",
                "risk_alert": "protocol_risk_change",
                "suspicious_activity": "suspicious_address_detected",
            }
            ws_alert_type = alert_type_map.get(
                exploit_data.get("type", "exploit_alert"), "exploit_alert_triggered"
            )
            publish_alert(ws_alert_type, exploit_data)
        except ImportError:
            logger.warning("WebSocket alerts system not available")

    except Exception as e:
        logger.error(f"Error in format_and_publish_exploit_alert: {e}")


# Example usage
if __name__ == "__main__":
    formatter = AlertFormatter()

    # Example whale data
    whale_data = {
        "whale_name": "Binance: Hot Wallet",
        "amount_usd": 2500000,
        "amount_eth": 750.5,
        "direction": "SELL",
        "token": "ETH",
        "chain": "ethereum",
        "exchange": "Uniswap",
        "from_address": "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be",
        "risk_level": "HIGH",
        "ml_dump_probability": 78.5,
        "ml_confidence_score": 0.82,
        "ml_estimated_impact": 3.2,
        "intent_classification": "AGGRESSIVE",
        "behavioral_pattern": "DISTRIBUTION",
        "timestamp": int(datetime.now().timestamp()),
    }

    alert = formatter.format_whale_alert(whale_data)
    discord_format = formatter.format_for_discord(alert)
    telegram_format = formatter.format_for_telegram(alert)

    print("Discord Format:")
    print(json.dumps(discord_format, indent=2))
    print("\nTelegram Format:")
    print(telegram_format)
