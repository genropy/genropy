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

        :param model: a model name, an alias (``low``, ``medium``, ``max``),
                      or ``None`` to use the service default.
        :returns: the resolved model identifier.
        """
        if model is None:
            return self.model
        if model in self._model_aliases:
            return self._model_aliases[model] or self.model
        return model or self.model

    def complete(self, system_prompt=None, user_prompt=None,
                 temperature=0, max_tokens=2000, model=None, **kwargs):
        """Send a prompt to the LLM and return the response.

        :param system_prompt: system-level instructions for the model.
        :param user_prompt: the user message to send.
        :param temperature: sampling temperature (0 = deterministic).
        :param max_tokens: maximum tokens to generate.
        :param model: model name, alias (``low``/``medium``/``max``), or
                      ``None`` for the service default. Aliases are resolved
                      via :meth:`resolve_model`.
        :param kwargs: provider-specific parameters.
        :returns: a dictionary with at least the following keys:

            - ``answer`` (str): the generated text.
            - ``model`` (str): the model used.
            - ``usage`` (dict, optional): token usage with keys
              ``prompt_tokens``, ``completion_tokens``, ``total_tokens``.
        """
        raise NotImplementedError
