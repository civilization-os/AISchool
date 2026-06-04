import MarkdownIt from 'markdown-it'
import mk from 'markdown-it-katex'
import hljs from 'highlight.js'

const md = new MarkdownIt({
    html: true,
    breaks: true,
    linkify: true,
    highlight: (code: string, lang: string) => {
        const h = lang && hljs.getLanguage(lang)
            ? hljs.highlight(code, { language: lang, ignoreIllegals: true }).value
            : hljs.highlightAuto(code).value;

        return `<div class="premium-code-block">
            <div class="code-header">
                <div class="controls"><span class="close"></span><span class="minimize"></span><span class="maximize"></span></div>
                <div class="lang-badge">${lang || 'code'}</div>
            </div>
            <pre class="hljs-block"><code class="hljs ${lang ? 'language-' + lang : ''}">${h}</code></pre>
        </div>`
    }
})

md.use(mk)

/**
 * 将层级列表文本转换为 Premium UI 树形组件
 */
function convertHierarchyToPremiumTree(text: string): string {
    const lines = text.split('\n').filter(l => l.trim())
    if (!lines.some(l => /[├└│]/.test(l))) return text

    let html = '<div class="tree-container">'

    // 识别标题/根节点：第一行如果不包含层级符号，则视为根
    let startIdx = 0
    const firstLine = lines[0]
    if (!/[├└│]/.test(firstLine)) {
        html += `<div class="tree-root"><span class="node-icon">🎯</span>${escapeHtml(firstLine.trim())}</div>`
        startIdx = 1
    }

    html += '<div class="tree-content">'
    
    for (let i = startIdx; i < lines.length; i++) {
        const line = lines[i]
        // 计算深度：根据开头的空格和层级符号数量
        const prefixMatch = line.match(/^[ \t│├└─]*/)
        const prefix = prefixMatch ? prefixMatch[0] : ''
        const depth = (prefix.match(/[│├└]/g) || []).length || 1
        
        const content = line.replace(/^[ \t│├└─]+/, '').trim()
        if (content) {
            // 根据内容匹配图标
            let icon = '🔗'
            if (/环境|系统|平台|架构/.test(content)) icon = '💻'
            else if (/核心|重点|考点|必考/.test(content)) icon = '🔥'
            else if (/语法|基础|定义|变量/.test(content)) icon = '📝'
            else if (/运算|算术|逻辑|处理/.test(content)) icon = '⚙️'
            else if (/模块|项目|工程/.test(content)) icon = '📦'
            
            html += `
                <div class="tree-node" style="padding-left: ${(depth - 1) * 20}px">
                    <div class="node-content">
                        <span class="node-icon">${icon}</span>
                        ${escapeHtml(content)}
                    </div>
                </div>`
        }
    }

    html += '</div></div>'
    return html
}

function escapeHtml(unsafe: string): string {
    return unsafe
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}

export function renderMd(text: string | null | undefined): string {
    if (!text) return ''

    try {
        let p = text

        // 0. 特殊处理：层级板书转 Premium Tree
        // 匹配包含层级符号的段落，支持 ├, └, │, ─ 等符号，不再硬性限制关键词
        const treePattern = /((?:\n|^)(?:[^\n]*)(?:\n[ \t]*[│├└][─│ \t]+[^\n]*)+)/g
        p = p.replace(treePattern, (match) => {
            return convertHierarchyToPremiumTree(match)
        })

        // 1. 处理 \[ ... \] 和 \begin{...} ... \end{...} 为块级公式 $$ 并包裹在 Spotlight 容器中
        p = p.replace(/\\\[([\s\S]*?)\\\]/g, (_, p1) => `\n\n<div class="formula-spotlight">\n\n$$\n${p1.trim()}\n$$\n\n</div>\n\n`)
            .replace(/\\begin\{([a-z*]+)\}([\s\S]*?)\\end\{\1\}/gi, (_, env, content) => {
                return `\n\n<div class="formula-spotlight">\n\n$$\n\\begin{${env}}${content}\\end{${env}}\n$$\n\n</div>\n\n`
            })
            // 2. 将 \( ... \) 转换为行内公式 $
            .replace(/\\\(([\s\S]*?)\\\)/g, (_, p1) => `$${p1.trim()}$`)

        // 3. 增强对 $ ... $ 的识别
        p = p.replace(/(^|[^$])\$((?:\\\$|[^$]){1,500}?)\$([^$]|$)/g, (_, pre, content, post) => {
            return `${pre}$${content.trim()}$${post}`
        })

        return md.render(p)
    } catch (e) {
        console.error('Markdown Render Error:', e)
        return String(text)
    }
}
