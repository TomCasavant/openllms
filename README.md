# OpenLLMs
OpenLLMs was a project investigating the use of LLMs across different sites and experimenting w/ using those LLMs in a different context. Uses as few external packages as possible, and flask[async] primarily so it could be easily compatible with the Maubot plugin system. 

## Usage:
Primarily intended to be used as a package in other projects, but it does include a few sample scripts.

### chat.py: 
Provides a basic chat interface to talk with all of the LLMs.
```console
python chat.py
```
It will prompt you for input, when you `@` mention a bot (e.g. `@substack hello!`) it will query that bot and respond to your message.

### ollama_server.py
Mimics the Ollama API.
I do *NOT* recommend using this in production. It was primarily for experimenting w/ various plugins that use ollama.

```console
python ollama_server.py
```
Boots up a flask server at port `:11434`. Download any software that uses ollama, for example the [Ollama Home Assistant integration](https://www.home-assistant.io/integrations/ollama/) and connect it to your flask server. Your application should be able to recognize all of the available LLMs. 
*Technically* it supports tool calling, but that was added very late into the process and it was only tested with Home Assistant. 

## Example Prompts:

AT&T:
```

```

Shopify Home Assistant:
```

```

Substack Code Assistant:
```

```


# Extension
[Maubot Plugin](https://github.com/TomCasavant/openllms-maubot)
