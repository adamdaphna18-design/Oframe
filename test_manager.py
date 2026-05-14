from oframe.plugin_manager import PluginManager

def main():
    manager = PluginManager()
    plugins = manager.load_plugins()

    print(f"Loaded plugins: {list(plugins.keys())}")

    if 'MoatAnalyzer' in plugins:
        print("MoatAnalyzer found. Testing run...")
        result = manager.run_plugin('MoatAnalyzer', idea_context="A highly commoditized widget")
        print(f"Result: {result}")
        assert result['risk_score'] == 10
        print("Test passed.")
    else:
        print("MoatAnalyzer not found.")
        assert False

if __name__ == "__main__":
    main()
