-- Sample Lua file for testing extraction

local M = {}

-- Module-level function with dot syntax
function M.greet(name)
    return "Hello " .. name
end

-- Method with colon syntax (implicit self)
function M:add(a, b)
    return a + b
end

-- Local function
local function helper()
    return 42
end

-- Table as config/class
M.config = {
    version = "1.0",
    debug = false,
}

-- Another module function
function M.configure(opts)
    M.config = opts
end

require("base")
local utils = require("utils")

return M
