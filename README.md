# VNamer

Is an AI renamer, you give it a lua script and it: 

- Look for variables and parameters with junk names
- Study what is assigned to those variables to make up a name, study the entire function

that uses those parameter to decide a name
Inspired by Oracle's AI renamer

uses Ollama and Qwen2.5b-coder:7b because nobody is spending money on AI for this

this uses master prompting and the AI goes through 3 stages of self correction to prevent AI hallucinating and give you the best result 

# Installation 

1. Install Ollama on the official page
2. Open ollama until you see a GUI, you can close it afterwards cause it runs in the background 
3. Open up terminal and type
```ollama pull qwen2.5b-coder:7b```

# How to use 

Open the batch script to start a webserver, then use this script to send a request to localhost:5000/rename
```lua
print("Hello World")
```

# Caution

Because free AIs have intelligence limitations, only use this on scripts less then 300 lines, because the AI will start hallucinating by either NOT follow the prompt or give you a summary of what the script does 
