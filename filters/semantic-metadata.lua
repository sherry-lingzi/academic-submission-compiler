-- Converts semantic YAML fields into styled DOCX blocks without changing source Markdown.

local stringify = pandoc.utils.stringify

local function flag(meta, name)
  if meta[name] == nil then return false end
  local value = stringify(meta[name]):lower()
  return value == 'true' or value == 'yes' or value == '1'
end

local function styled_para(style, label_style, body_style, label, value)
  local content = {
    pandoc.Span({pandoc.Str(label)}, pandoc.Attr('', {}, {['custom-style'] = label_style})),
    pandoc.Span({pandoc.Str(stringify(value))}, pandoc.Attr('', {}, {['custom-style'] = body_style}))
  }
  return pandoc.Div({pandoc.Para(content)}, pandoc.Attr('', {}, {['custom-style'] = style}))
end

local function list_text(value, separator)
  local parts = {}
  if value then
    for _, item in ipairs(value) do table.insert(parts, stringify(item)) end
  end
  return table.concat(parts, separator)
end

function Meta(meta)
  if meta.authors and not meta.author and not flag(meta, 'asc-hide-authors') then
    local authors = pandoc.MetaList({})
    for _, author in ipairs(meta.authors) do
      if author.name then authors:insert(author.name) else authors:insert(author) end
    end
    meta.author = authors
  end
  if flag(meta, 'asc-hide-authors') then meta.author = nil end
  if flag(meta, 'asc-hide-email') then meta.email = nil end
  if flag(meta, 'asc-hide-orcid') then meta.orcid = nil end
  if flag(meta, 'asc-hide-correspondence') then meta.correspondence = nil end
  if flag(meta, 'asc-hide-acknowledgements') then meta.acknowledgements = nil end
  return meta
end

function Pandoc(doc)
  local meta = doc.meta
  local blocks = pandoc.List()
  if not flag(meta, 'asc-hide-affiliations') and meta.authors then
    local affiliations = {}
    for _, author in ipairs(meta.authors) do
      if author.affiliation then table.insert(affiliations, stringify(author.affiliation)) end
    end
    if #affiliations > 0 then
      blocks:insert(pandoc.Div({pandoc.Para({pandoc.Str('单位：' .. table.concat(affiliations, '；'))})}, pandoc.Attr('', {}, {['custom-style'] = 'Affiliation'})))
    end
  end
  if meta.abstract then
    if meta.abstract.zh then blocks:insert(styled_para('Abstract', 'Abstract zh Label', 'Abstract zh Body', '摘要：', meta.abstract.zh)) end
    if meta.abstract.en then blocks:insert(styled_para('Abstract', 'Abstract en Label', 'Abstract en Body', 'Abstract: ', meta.abstract.en)) end
  end
  if meta.keywords then
    local zh_separator = meta['asc-keywords-zh-separator'] and stringify(meta['asc-keywords-zh-separator']) or '；'
    local en_separator = meta['asc-keywords-en-separator'] and stringify(meta['asc-keywords-en-separator']) or '; '
    if meta.keywords.zh then blocks:insert(styled_para('Keywords', 'Keywords zh Label', 'Keywords zh Body', '关键词：', list_text(meta.keywords.zh, zh_separator))) end
    if meta.keywords.en then blocks:insert(styled_para('Keywords', 'Keywords en Label', 'Keywords en Body', 'Keywords: ', list_text(meta.keywords.en, en_separator))) end
  end
  if not flag(meta, 'asc-hide-funding') and meta.funding then
    local funding = {}
    for _, item in ipairs(meta.funding) do
      local text = item.name and stringify(item.name) or stringify(item)
      if item.number then text = text .. '（' .. stringify(item.number) .. '）' end
      table.insert(funding, text)
    end
    blocks:insert(pandoc.Div({pandoc.Para({pandoc.Str('基金项目：' .. table.concat(funding, '；'))})}, pandoc.Attr('', {}, {['custom-style'] = 'Funding'})))
  end
  blocks:extend(doc.blocks)
  doc.blocks = blocks
  return doc
end
