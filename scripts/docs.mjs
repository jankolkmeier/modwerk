import { execFileSync } from 'node:child_process'
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { refuseNewEntries } from './changelog.mjs'

/** The documents every agent reads stay short enough to read in one go: one may grow to LIMIT bytes, and one already
 * longer may not grow at all. The two old logs are frozen; a new record is its own dated file (docs/README.md). */
export const LIMIT = 32 * 1024
export const FROZEN = { 'docs/VERIFICATION.md': 'docs/verification/', 'docs/DECISIONS.md': 'docs/decisions/' }
const RECORD = /^\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*\.md$/

function markdownUnder(root, folder) {
  if (!existsSync(join(root, folder))) return []
  return readdirSync(join(root, folder)).sort().flatMap(name => {
    const path = folder + '/' + name
    return statSync(join(root, path)).isDirectory() ? markdownUnder(root, path) : name.endsWith('.md') ? [path] : []
  })
}

// Line endings are counted as in Git, so a Windows checkout measures the same size.
const size = text => Buffer.byteLength(text.replace(/\r\n/g, '\n'))
function sizeAt(root, base, file) {
  try { return size(execFileSync('git', ['show', base + ':' + file], { cwd: root, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], maxBuffer: 32 * 1024 * 1024 })) } catch { return 0 }
}
const kb = bytes => (bytes / 1024).toFixed(1) + ' KB'

/** Record files are named by date; with a base commit, no document outgrew the limit and no frozen log took a new record. */
export function checkDocs(root, base = null) {
  const problems = []
  for (const folder of Object.values(FROZEN)) {
    for (const file of markdownUnder(root, folder.slice(0, -1))) {
      if (!RECORD.test(file.slice(folder.length))) problems.push(`${file}: name each record ${folder}<YYYY-MM-DD>-<topic>.md, in lowercase words joined by hyphens.`)
    }
  }
  const documents = ['AGENTS.md', ...markdownUnder(root, 'docs')].filter(file => existsSync(join(root, file)) && !(file in FROZEN))
  if (base) {
    for (const [file, folder] of Object.entries(FROZEN)) {
      try { refuseNewEntries(root, base, file, `frozen on 25 October 2026. Put a new record in its own file, ${folder}<YYYY-MM-DD>-<topic>.md.`) } catch (error) { problems.push(error.message) }
    }
    const grown = documents.flatMap(file => {
      const now = size(readFileSync(join(root, file), 'utf8'))
      if (now <= LIMIT) return []
      const before = sizeAt(root, base, file)
      return now > before ? [before ? `${file} grew by ${now - before} bytes to ${kb(now)}` : `${file} is new at ${kb(now)}`] : []
    })
    if (grown.length) problems.push(`${grown.join('; ')}, over the ${kb(LIMIT)} a document may have. Make room by cutting what is stale or said elsewhere (Git keeps the history), or move a part into its own document and list it in docs/README.md.`)
  }
  if (problems.length) throw new Error(problems.join('\n'))
  return { documents: documents.length }
}
