# VNamer

Is an AI renamer, you give it a lua script and it: 

- Look for variables and parameters with junk names
- Study what is assigned to those variables to make up a name, study entire functions that uses those parameter to decide a name

Inspired by Oracle's AI renamer, uses Ollama and Qwen2.5b-coder:7b because nobody is spending money on AI for this

this uses master prompting and the AI goes through 3 stages of self correction to prevent AI hallucinating and give you the best result 

# Installation 

1. Install Ollama on the official page
2. Open Ollama until you see a GUI, you can close it afterwards cause it runs in the background 
3. Open up terminal and type
```ollama pull qwen2.5b-coder:7b```

# How to use 

Open the batch script to start a webserver, use this script to send a request to http://127.0.0.1:5000/rename

```lua
local HS = game:GetService("HttpService")
local Req = request or http_request

if not isfolder("VNamer") then makefolder("VNamer") end
if not isfile("VNamer/Input.lua") then writefile("VNamer/Input.lua") end

local Source = readfile("VNamer/Input.lua")
assert(Source ~= "", "[VNamer] Paste your script into VNamer/Input.lua first")

local Res = Req({
	Url = "http://127.0.0.1:5000/rewrite",
	Method = "POST",
	Headers = { ["Content-Type"] = "application/json" },
	Body = HS:JSONEncode({ script = Source }),
})

local Data = HS:JSONDecode(Res.Body)
writefile("VNamer/Output.lua", Data.fixed_script)
```

After you run this, put your script in VNamer/Input.lua then run it again 

# Caution

Because free AIs have intelligence limitations, only use this on scripts less then 500 lines, because the AI will start hallucinating by either NOT follow the prompt or give you a summary of what the script does 

When decompiling, you cannot retrieve variable names except do a few hacks like make every GetService variable names the thing in quotes.
This project is made to see how AI could fix decompiled scripts, this should not be released for production or for sale without perfect tuning and measures, it is simply a concept 
