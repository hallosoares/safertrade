# SaferTrade API Schema Documentation

## Overview

The SaferTrade API provides standardized, versioned JSON schemas for consuming MEV protection and security signals from the SaferTrade platform.

## Schema Version: v1.0

### Core Signal Structure

All signals follow a consistent structure with required metadata and signal-specific data:

```json
{
  "signal_type": "string",      // Required: Type of signal  
  "timestamp": "number",        // Required: Unix timestamp
  "confidence": "number",       // Required: 0-100 confidence score
  "data_source": "string",      // Required: Generating component
  "version": "string",          // Required: Schema version (v1.0)
  "tenant_id": "string",        // Optional: Tenant identifier
  "processing_time": "number",  // Optional: Processing time (ms)
  "explanation": "string",      // Optional: Human-readable description
  "signal_data": "object",      // Signal-specific payload
  "metadata": "object"          // Optional: Additional context
}
```

### Field Definitions

#### Core Fields

- **signal_type**: Enum of supported signal types
  - `gap_detection`: Price gap arbitrage opportunities
  - `bridge_arbitrage`: Cross-chain arbitrage via bridges
  - `cross_chain_arbitrage`: Generic cross-chain opportunities
  - `flash_loan_opportunity`: Flash loan arbitrage signals

- **timestamp**: Unix timestamp (seconds) when signal was generated

- **confidence**: Integer 0-100 representing signal quality/confidence
  - 0-30: Low confidence, high risk
  - 31-70: Medium confidence, moderate risk
  - 71-100: High confidence, low risk

- **data_source**: Component that generated the signal
  - `gap_finder`: Gap detection engine
  - `bridge_arbitrage`: Bridge arbitrage monitor
  - `flash_loan_monitor`: Flash loan opportunity scanner

- **version**: Schema version string (pattern: `v\d+\.\d+`)

#### Optional Fields

- **tenant_id**: Multi-tenant identifier for signal routing
- **processing_time**: Signal generation time in milliseconds
- **explanation**: Human-readable signal description
- **metadata**: Additional context (chain ID, block number, gas prices, etc.)

### Signal Types

#### Gap Detection Signals

Gap detection signals identify price differences across DEX pools:

```json
{
  "signal_type": "gap_detection",
  "signal_data": {
    "type": "good_arbitrage",        // Classification: good_arbitrage, bad_arbitrage, bad_arb
    "pool_depth_usd": "750000",      // Pool liquidity in USD
    "est_edge_bps": "20",            // Estimated edge in basis points
    "notional_usd": "12000",         // Trade size in USD
    "gas_gwei": "30",                // Current gas price
    "text": "High-quality ETH arbitrage"  // Description
  }
}
```

#### Bridge Arbitrage Signals

Bridge arbitrage signals identify cross-chain price differences:

```json
{
  "signal_type": "bridge_arbitrage",
  "signal_data": {
    "bridge": "arbitrum",               // Bridge protocol
    "route": "ethereum -> arbitrum",    // Chain route
    "token": "USDC",                    // Token symbol
    "profit_usd": "245.67",             // Expected profit USD
    "profit_pct": "1.23",               // Profit percentage
    "capital_required": "20000.00",     // Required capital USD
    "delay_sec": "180"                  // Execution delay seconds
  }
}
```

### Metadata Fields

Optional metadata provides execution context:

- **chain_id**: Blockchain network identifier
- **block_number**: Block when opportunity was detected
- **transaction_hash**: Related transaction (if applicable)
- **gas_price_gwei**: Current gas price in gwei
- **estimated_execution_time**: Expected execution time (seconds)

## Versioning Strategy

### Version Format
- Pattern: `vMAJOR.MINOR`
- Example: `v1.0`, `v1.1`, `v2.0`

### Version Compatibility

- **Major version changes** (v1.0 → v2.0): Breaking changes
  - Field removals or type changes
  - Required field additions
  - Enum value removals

- **Minor version changes** (v1.0 → v1.1): Backward compatible
  - Optional field additions
  - Enum value additions
  - Documentation updates

### Migration Path

Clients should:
1. Always check the `version` field in received signals
2. Implement fallback handling for unknown fields
3. Log warnings for deprecated versions
4. Plan upgrades for major version changes

## Usage Examples

### Consuming Signals

```python
import json
import jsonschema

# Load schema
with open('schemas/signals_v1.json') as f:
    schema = json.load(f)

# Validate incoming signal
def validate_signal(signal_data):
    try:
        jsonschema.validate(signal_data, schema)
        return True
    except jsonschema.ValidationError as e:
        print(f"Invalid signal: {e}")
        return False

# Process signal based on type
def process_signal(signal):
    if not validate_signal(signal):
        return
        
    signal_type = signal['signal_type']
    confidence = signal['confidence']
    
    if signal_type == 'gap_detection' and confidence > 70:
        handle_gap_signal(signal)
    elif signal_type == 'bridge_arbitrage' and confidence > 80:
        handle_bridge_signal(signal)
```

### Schema Evolution

Future signal types can be added by extending the schema:

```json
{
  "signal_type": "liquidation_opportunity",
  "signal_data": {
    "protocol": "compound",
    "account": "0x...",
    "collateral_token": "ETH",
    "debt_token": "USDC",
    "liquidation_bonus": "5.0",
    "health_factor": "0.95"
  }
}
```

## Integration Notes

### Redis Stream Format

Signals are published to Redis streams with the signal JSON as the `data` field:

```
XADD safertrade.detections * data '{"signal_type":"gap_detection",...}'
```

### Error Handling

Clients should handle:
- Schema validation failures
- Missing required fields
- Unknown signal types
- Version compatibility issues

### Performance Considerations

- Signal processing should be non-blocking
- High-frequency signals may require batching
- Consider confidence thresholds for filtering
- Monitor processing times for optimization

---

*Schema Version: v1.0*  
*Last Updated: 2025-09-13*  
*SaferTrade Protection Platform*
