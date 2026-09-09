-- Converts semantic YAML fields into styled DOCX blocks without changing source Markdown.

local stringify = pandoc.utils.stringify

local function styled_para(style, label, value)
  local text = label .. stringify(value)
  return pandoc.Div({pandoc.Para({pandoc.Str(text)})}, pandoc.Attr('', {}, {['custom-style'] = style}))
end

local function list_text(value)
  local parts = {}
  if value then
    for _, item in ipairs(value) do table.insert(parts, stringify(item)) end
  end
  return table.concat(parts, '；')
end

function Meta(meta)
  if meta.authors and not meta.author then
    local authors = pandoc.MetaList({})
    for _, author in ipairs(meta.authors) do
      if author.name then authors:insert(author.name) else authors:insert(author) end
    end
    meta.author = authors
  end
  if meta['asc-anonymous'] then
    meta.author = nil
  end
  return meta
end

function Pandoc(doc)
  local meta = doc.meta
  local blocks = pandoc.List()
  local anonymous = meta['asc-anonymous'] ~= nil
  if not anonymous and meta.authors then
    local affiliations = {}
    for _, author in ipairs(meta.authors) do
      if author.affiliation then table.insert(affiliations, stringify(author.affiliation)) end
    end
    if #affiliations > 0 then blocks:insert(styled_para('Affiliation', '单位：', table.concat(affiliations, '；'))) end
  end
  if meta.abstract then
    if meta.abstract.zh then blocks:insert(styled_para('Abstract', '摘要：', meta.abstract.zh)) end
    if meta.abstract.en then blocks:insert(styled_para('Abstract', 'Abstract: ', meta.abstract.en)) end
  end
  if meta.keywords then
    if meta.keywords.zh then blocks:insert(styled_para('Keywords', '关键词：', list_text(meta.keywords.zh))) end
    if meta.keywords.en then blocks:insert(styled_para('Keywords', 'Keywords: ', list_text(meta.keywords.en))) end
  end
  if not anonymous and meta.funding then
    local funding = {}
    for _, item in ipairs(meta.funding) do
      local text = item.name and stringify(item.name) or stringify(item)
      if item.number then text = text .. '（' .. stringify(item.number) .. '）' end
      table.insert(funding, text)
    end
    blocks:insert(styled_para('Funding', '基金项目：', table.concat(funding, '；')))
  end
  blocks:extend(doc.blocks)
  doc.blocks = blocks
  return doc
end

