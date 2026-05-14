from oframe.plugin_interface import OPlugin

class MoatAnalyzer(OPlugin):
    def run(self, idea_context: str):
        # 1. Simulate asking an AI model to find potential 'Sherlocking' risks
        if self.core and hasattr(self.core, 'ask_ollama'):
            prompt = f"Analyze the competitive moat for this idea: {idea_context}"
            analysis = self.core.ask_ollama(prompt)
        else:
            # Fallback mock analysis
            analysis = f"Mock analysis: {idea_context} has low risk."
            if "commoditized" in idea_context.lower():
                 analysis = f"Mock analysis: {idea_context} is highly commoditized."

        # 2. Assign a risk score
        risk_score = 10 if "commoditized" in analysis.lower() else 2

        return {
            "moat_analysis": analysis,
            "risk_score": risk_score
        }
