#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gnr.lib.services import GnrBaseService


class LlmService(GnrBaseService):
    """Base class for LLM (Large Language Model) service implementations.

    Subclasses must implement :meth:`complete` to interact with a specific
    LLM provider (Anthropic, OpenAI, etc.).

    Model aliases allow callers to request a capability tier (``low``,
    ``medium``, ``max``) instead of a specific model name.  Each
    implementation provides sensible defaults that can be overridden
    via the service configuration UI.

    Usage from a GenroPy page or component::

        service = self.getService('llm')
        result = service.complete(
            system_prompt='You are a helpful assistant.',
            user_prompt='What is 2+2?',
            temperature=0,
            max_tokens=500,
            model='low'  # uses the low-tier model alias
        )
        answer = result['answer']
    """

    def __init__(self, parent, model=None,
                 model_low=None, model_medium=None, model_max=None,
                 **kwargs):
        self.parent = parent
        self.model = model
        self._model_aliases = {
            'low': model_low,
            'medium': model_medium,
            'max': model_max,
        }

    def resolve_model(self, model=None):
        """Resolve a model name or alias to an actual model identifier.

        Args:
            model: A model name, an alias (``low``, ``medium``, ``max``),
                   or ``None`` to use the service default.

        Returns:
            str: The resolved model identifier.
        """
        if model is None:
            return self.model
        return self._model_aliases.get(model) or model or self.model

    def complete(self, system_prompt=None, user_prompt=None,
                 temperature=0, max_tokens=2000, model=None, **kwargs):
        """Send a prompt to the LLM and return the response.

        Args:
            system_prompt: System-level instructions for the model.
            user_prompt: The user message to send.
            temperature: Sampling temperature (0 = deterministic).
            max_tokens: Maximum tokens to generate.
            model: Model name, alias (``low``/``medium``/``max``), or
                   ``None`` for the service default.  Aliases are resolved
                   via :meth:`resolve_model`.
            **kwargs: Provider-specific parameters.

        Returns:
            dict: A dictionary with at least the following keys:

            - ``answer`` (str): The generated text.
            - ``model`` (str): The model used.
            - ``usage`` (dict, optional): Token usage with keys
              ``prompt_tokens``, ``completion_tokens``, ``total_tokens``.
        """
        raise NotImplementedError
