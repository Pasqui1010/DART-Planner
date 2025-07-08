from dart_planner.common.errors import UnsupportedCommandError

# Example mission logic for robust command dispatch
async def safe_send_command(adapter, command, params=None):
    capabilities = adapter.get_capabilities()
    if "supported_commands" in capabilities and command not in capabilities["supported_commands"]:
        print(f"Command '{command}' not supported by this adapter (checked via capabilities). Skipping.")
        return None
    try:
        result = adapter.send_command(command, params)
        print(f"Command '{command}' executed successfully: {result}")
        return result
    except UnsupportedCommandError as e:
        print(f"Command '{command}' is not supported (caught exception): {e}")
        # Handle gracefully, e.g., log, skip, or fallback
        return None
    except Exception as e:
        print(f"Unexpected error while sending command '{command}': {e}")
        raise 