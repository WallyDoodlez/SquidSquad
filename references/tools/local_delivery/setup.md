# Local delivery — setup

No setup is required. This is a built-in capability — deliveries are
plain folders the delivery manager writes directly to disk, ready for
a human or operator to forward through whatever external channel the
project uses.

There is no account to create, no MCP server to install, and no
credentials to configure. If the delivery manager can write files
on this machine, the tool is already working.

## Optional — configure a delivery destination

By default the delivery manager writes to its own per-agent folder.
If the project has a preferred parent directory (for example a
shared network drive or a synced folder), share the path with the
delivery manager the first time it picks up a delivery task — it
will use that path from then on.
