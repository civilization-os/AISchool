import { describe, it, expect } from 'vitest'
import { renderMd } from './markdown'

describe('Markdown Utility', () => {
  it('should render simple markdown to html', () => {
    const md = '# Hello'
    const html = renderMd(md)
    expect(html).toContain('<h1>Hello</h1>')
  })

  it('should convert hierarchy text to premium tree', () => {
    const treeText = '\nPython\n├── 变量\n└── 循环\n'
    const html = renderMd(treeText)
    expect(html).toContain('tree-container')
    expect(html).toContain('tree-root')
    expect(html).toContain('Python')
    expect(html).toContain('变量')
    expect(html).toContain('循环')
  })

  it('should handle nested trees correctly', () => {
    const treeText = '\nRoot\n│ ├── Child 1\n│ └── Child 2\n'
    const html = renderMd(treeText)
    expect(html).toContain('tree-node')
    // Check if paddings are applied for depth
    expect(html).toContain('padding-left: 20px')
  })

  it('should escape HTML in tree content', () => {
    const treeText = '\nRoot\n├── <script>alert(1)</script>\n'
    const html = renderMd(treeText)
    expect(html).not.toContain('<script>')
    expect(html).toContain('&lt;script&gt;')
  })

  it('should wrap formulas in spotlight containers', () => {
    const formula = '\\[ x^2 + y^2 = z^2 \\]'
    const html = renderMd(formula)
    expect(html).toContain('formula-spotlight')
    expect(html).toContain('$$')
  })
})
