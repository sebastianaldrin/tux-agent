"""
TuxAgent Model Constants - Single Source of Truth
Centralized model identifier for the entire application
"""


class TuxAgentModels:
    """
    Single source of truth for model identifiers.

    TuxAgent uses Kimi K2.5 for multimodal (vision + text + tools) capabilities.
    Change the model here to update throughout the entire application.
    """

    # Primary multimodal model - handles vision, text, and tools
    PRIMARY_MODEL = "moonshotai/kimi-k2.5"

    # Model capabilities
    SUPPORTS_VISION = True
    SUPPORTS_TOOLS = True
    MAX_CONTEXT = 256000  # 256K context window

    @classmethod
    def get_primary_model(cls) -> str:
        """Get the primary model ID used by TuxAgent"""
        return cls.PRIMARY_MODEL

    @classmethod
    def get_model_info(cls) -> dict:
        """Get model information"""
        return {
            "model_id": cls.PRIMARY_MODEL,
            "provider": "Together.ai",
            "supports_vision": cls.SUPPORTS_VISION,
            "supports_tools": cls.SUPPORTS_TOOLS,
            "max_context": cls.MAX_CONTEXT,
            "cost_per_mtok_input": 0.50,
            "cost_per_mtok_output": 2.80
        }


# Convenience constant for direct imports
KIMI_MODEL = TuxAgentModels.PRIMARY_MODEL
