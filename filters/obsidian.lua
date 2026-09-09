-- MIT License. Original implementation for Academic Submission Compiler.
-- Uses Pandoc's AST instead of broad source-text replacement.

local function is_wikilink(link)
  return link.title == 'wikilink' or link.target:match('%.md#?') or link.target:match('^#')
end

function Inlines(inlines)
  local output = pandoc.List()
  local index = 1
  while index <= #inlines do
    local current = inlines[index]
    local following = inlines[index + 1]
    if current.t == 'Str' and current.text == '!' and following and following.t == 'Link' and is_wikilink(following) then
      local target = following.target:gsub('%%20', ' ')
      if target:lower():match('%.png$') or target:lower():match('%.jpe?g$') or target:lower():match('%.gif$') or target:lower():match('%.svg$') then
        output:insert(pandoc.Image({}, target))
      else
        output:insert(pandoc.Str('[嵌入笔记：'))
        output:extend(following.content)
        output:insert(pandoc.Str(']'))
      end
      index = index + 2
    elseif current.t == 'Link' and is_wikilink(current) then
      output:extend(current.content)
      index = index + 1
    else
      output:insert(current)
      index = index + 1
    end
  end
  return output
end

function BlockQuote(block)
  local first = block.content[1]
  if first and first.t == 'Para' and first.content[1] and first.content[1].t == 'Str' then
    local label = first.content[1].text:match('^%[!([A-Za-z]+)%]')
    if label then
      first.content[1] = pandoc.Strong({pandoc.Str(label .. ':')})
    end
  end
  return block
end
