# SmartThings MCP Implementation Reference

## 1. Authentication

### Personal Access Token (PAT)
- **Create at**: https://account.smartthings.com/tokens
- Sign in with Samsung account
- Select specific scopes (permissions) when creating
- **CRITICAL**: PATs created after Dec 30, 2024 are valid for only 24 hours
- Legacy PATs (before Dec 30, 2024) may be valid up to 50 years
- Token shown only once during creation - must copy immediately
- **For production**: Implement OAuth 2.0 flow for token refresh capability

### Authorization Header
```
Authorization: Bearer <TOKEN>
```

### Best Practice
Request minimal necessary scopes for security

---

## 2. Architecture & Core Concepts

### Organizational Hierarchy
- **Locations**: Top-level logical groupings (homes, offices)
  - Users can have up to 10 locations
  - Each has a unique `locationId`
- **Rooms**: Subdivisions within locations for organizing devices
- **Devices**: Physical products connected to SmartThings platform
- **Modes**: Location states (Away, Home, Night) used in automations

### Device Types
- **Hub Connected**: Matter, Zigbee, Z-Wave, LAN devices
- **Cloud Connected**: Third-party cloud integrations
- **Direct Connected**: WiFi devices
- **Mobile Connected**: Bluetooth devices via Samsung phones

### Capability Model
- Devices expose **capabilities** (e.g., "switch", "thermostat")
- Capabilities have:
  - **Commands**: Control actions (e.g., `on()`, `off()`)
  - **Attributes**: State properties (e.g., `switch: "on"`)
- **Components** organize capabilities (typically "main" component for primary functions)

---

## 3. API Endpoints

### Base URL
```
https://api.smartthings.com/v1/
```

### Required Headers
```
Authorization: Bearer <TOKEN>
Content-Type: application/json
```

### Locations
- `GET /locations` - List all accessible locations
- `GET /locations/{locationId}` - Get specific location details
- `DELETE /locations/{locationId}` - Delete location and all associated devices/apps

### Devices
- `GET /devices` - List all devices
- `GET /devices/{deviceId}` - Get device details
- `GET /devices/{deviceId}/status` - Get current device status (all capabilities/attributes)
- `POST /devices/{deviceId}/commands` - Execute commands on device
- `POST /devices` - Create new device
- `DELETE /devices/{deviceId}` - Delete device

### Command Execution Format
```json
{
  "commands": [
    {
      "component": "main",
      "capability": "switch",
      "command": "on"
    }
  ]
}
```
**Maximum 10 commands per request**

---

## 4. Device Capabilities Reference

### Common Control Capabilities

#### Switch
- **Attribute**: `switch` ("on"/"off")
- **Commands**: `on()`, `off()`

#### Switch Level (Dimmer)
- **Attribute**: `level` (0-100%)
- **Commands**: `setLevel(number, number)`

#### Lock
- **Attribute**: `lock` ("locked"/"unlocked")
- **Commands**: `lock()`, `unlock()`

#### Door Control
- **Attribute**: `door` ("open"/"closed"/"closing"/"opening"/"unknown")
- **Commands**: `open()`, `close()`

#### Thermostat
- **Attributes**:
  - `temperature`
  - `heatingSetpoint`
  - `coolingSetpoint`
  - `thermostatMode`
  - `thermostatFanMode`
  - `thermostatOperatingState`
- **Commands**:
  - `setHeatingSetpoint(number)`
  - `setCoolingSetpoint(number)`
  - `heat()`
  - `cool()`
  - `off()`

#### Color Control
- **Attributes**: `hue`, `saturation`, `color`
- **Commands**:
  - `setHue(number)`
  - `setSaturation(number)`
  - `setColor(map)`

### Sensor Capabilities (Read-Only)

#### Motion Sensor
- **Attribute**: `motion` ("active"/"inactive")

#### Contact Sensor
- **Attribute**: `contact` ("open"/"closed")

#### Presence Sensor
- **Attribute**: `presence` ("present"/"not present")

#### Temperature Measurement
- **Attribute**: `temperature` (numeric)

#### Battery
- **Attribute**: `battery` (percentage)

### Full Capabilities Reference
https://developer.smartthings.com/docs/devices/capabilities/capabilities-reference

---

## 5. Rate Limits & Guardrails

### Guardrails (Maximum Counts)
- 10 locations per user
- 100 app installations per location
- 30 cloud-connected devices per installed app
- 40 subscriptions per installed app
- 35 apps per type per user
- **10 commands max per request**

### Rate Limits (Throughput)
- 60 requests/minute for most app APIs
- 12 requests/minute per device operation
- 50 requests/hour for rooms
- 50 requests/minute per scene
- 40 subscription create requests per 15 minutes

### Event Limits
- 10 KiB max event size
- Devices should emit max 1 event/minute (unless user-triggered)

### Rate Limit Response Headers
```
X-RateLimit-Limit: <max requests per window>
X-RateLimit-Remaining: <remaining requests>
X-RateLimit-Reset: <seconds until reset>
```

**Response**: HTTP 429 when rate limit exceeded

---

## 6. Error Handling

### Error Response Structure
```json
{
  "requestId": "031fec1a-f19f-470a-a7da-710569082846",
  "error": {
    "code": "ConstraintViolationError",
    "message": "Validation errors occurred...",
    "details": [...]
  }
}
```

### HTTP Status Codes
- `200` - Success
- `400` - Bad Request (malformed request)
- `401` - Unauthorized (authentication failed)
- `403` - Forbidden (valid auth but insufficient permissions)
- `404` - Not Found
- `422` - Unprocessable Entity (constraint/validation error, guardrail exceeded)
- `429` - Too Many Requests (rate limit exceeded)

### Error Handling Strategy
- Capture and expose `requestId` for debugging
- Implement retry logic for 429 errors with exponential backoff
- Validate scopes/permissions for 401/403 errors
- Provide clear user feedback for constraint violations (422)

---

## 7. Webhooks & Real-Time Events

### Enterprise Eventing
- Account-level event delivery system
- **Components**:
  - **Sinks**: Webhook endpoints
  - **Subscriptions**: Event filters
  - **Events**: Notifications
- SmartThings sends POST requests to webhook endpoints with event batches
- Enables near real-time device state updates with minimal network traffic

### Subscription Event Types
- Device state changes
- Lifecycle events
- Location/mode changes

### Benefits
- Minimal polling needed
- Real-time state synchronization
- Scalable for enterprise deployments

---

## 8. MCP Implementation Notes

### Critical Considerations
1. **Store PAT securely** - Use environment variable or config file
2. **Handle 24-hour PAT expiration** - Warn users or implement OAuth
3. **Implement rate limit tracking** - Use response headers
4. **Validate capability support** - Before sending commands
5. **Include requestId in error logs** - For troubleshooting
6. **Respect device event limits** - Max 1/minute
7. **Use component "main"** - For most device commands
8. **Maximum 10 commands per batch** - Per request limit

### Recommended Project Structure
```
smartthings-mcp/
├── src/
│   ├── index.ts              # MCP server entry
│   ├── api/
│   │   ├── client.ts         # SmartThings API client
│   │   ├── auth.ts           # PAT/OAuth handling
│   │   └── types.ts          # TypeScript interfaces
│   ├── tools/
│   │   ├── devices.ts        # Device control tools
│   │   ├── locations.ts      # Location management
│   │   ├── capabilities.ts   # Capability reference
│   │   └── status.ts         # Status queries
│   └── utils/
│       ├── errors.ts         # Error handling
│       └── rate-limit.ts     # Rate limit tracking
├── package.json
└── README.md
```

### Implementation Priority
1. **High Priority**:
   - API client with PAT authentication
   - Device listing and status queries
   - Core device commands (switch, lock, thermostat)

2. **Medium Priority**:
   - Location/room management
   - Additional capabilities (color, dimmer, sensors)
   - Batch command execution

3. **Low Priority**:
   - Webhook subscriptions
   - Advanced automations
   - Scene execution

---

## 9. Key Terminology

- **PAT**: Personal Access Token
- **Scope**: Permission granted to token
- **Component**: Logical division of device capabilities (usually "main")
- **Capability**: Standard interface for device functions
- **Command**: Action to control device
- **Attribute**: Device state property
- **Guardrail**: Maximum instance count limit
- **Rate Limit**: Request throughput limit
- **Sink**: Webhook endpoint for events
- **Subscription**: Event filter configuration

---

## 10. Useful Resources

- **API Documentation**: https://developer.smartthings.com/docs/api/public/
- **Architecture**: https://developer.smartthings.com/docs/getting-started/architecture-of-smartthings
- **Authorization**: https://developer.smartthings.com/docs/getting-started/authorization-and-permissions
- **Capabilities Reference**: https://developer.smartthings.com/docs/devices/capabilities/capabilities-reference
- **Rate Limits**: https://developer.smartthings.com/docs/getting-started/rate-limits
- **Create PAT**: https://account.smartthings.com/tokens
- **SmartThings CLI**: https://github.com/SmartThingsCommunity/smartthings-cli
