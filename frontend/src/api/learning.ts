/**
 * AI School 完整 API 层
 */

import axios from 'axios'

const api = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
    timeout: 120000,
    headers: { 'Content-Type': 'application/json' }
})

api.interceptors.response.use(
    r => r.data,
    err => {
        const msg = err.response?.data?.detail || err.message || '请求失败'
        return Promise.reject(new Error(msg))
    }
)

export { api }
export default api

// ── SSE 流式读取助手 ──────────────────────────────────────
const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

async function fetchStream(path: string, body: any, onChunk: (chunk: string) => void) {
    const res = await fetch(`${BASE_URL}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    })
    const reader = res.body?.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let finalResult = null

    while (reader) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        let boundary = buffer.indexOf('\n\n')
        while (boundary !== -1) {
            const message = buffer.slice(0, boundary)
            buffer = buffer.slice(boundary + 2)
            if (message.startsWith('data: ')) {
                try {
                    const data = JSON.parse(message.slice(6))
                    if (data.status === 'streaming') {
                        // 清除大模型带有的 markdown `` `json 和 `` ` 后缀
                        let cleanChunk = data.chunk
                            .replace(/```json\n?/g, '')
                            .replace(/```/g, '')
                        onChunk(cleanChunk)
                    } else if (data.status === 'done') {
                        finalResult = data
                    }
                } catch (e) { }
            }
            boundary = buffer.indexOf('\n\n')
        }
    }
    return finalResult
}

export const getSessionQuizzes = (sessionId: number) =>
    api.get(`/session/${sessionId}/quizzes`)

export const saveAssessmentAnswers = (sessionId: number, answers: string[]) =>
    api.post(`/assessment/save_answers/${sessionId}`, { answers })


// ── 知识问答助手 ──────────────────────────────────────────
export const checkHealth = () => api.get('/health')

// ── 会话管理 ──────────────────────────────────────────
export const createSession = (subject: string, studentName = '学习者', levels: number[] = [1]) =>
    api.post('/session/create', { subject, student_name: studentName, levels })

export const getSession = (sessionId: number) =>
    api.get(`/session/${sessionId}`)

export const deleteSession = (sessionId: number) =>
    api.delete(`/session/${sessionId}`)

export const getStudentSessions = (studentName = '学习者') =>
    api.get(`/session/student/${encodeURIComponent(studentName)}`)

// ── 入学测评 ──────────────────────────────────────────
export const startAssessment = (sessionId: number, openCount = 2, forceNew = false) =>
    api.post(`/assessment/start/${sessionId}?open_count=${openCount}&force_new=${forceNew}`)

export const startAssessmentStream = (sessionId: number, onChunk: (text: string) => void, openCount = 2, forceNew = false) =>
    fetchStream(`/assessment/start_stream/${sessionId}?open_count=${openCount}&force_new=${forceNew}`, {}, onChunk)

export const submitAssessment = (sessionId: number, answers: string[]) =>
    api.post(`/assessment/submit/${sessionId}`, { answers })

// ── 大纲（持久化）─────────────────────────────────────
export const generateSyllabusForSession = (sessionId: number, topic: string, force = false) =>
    api.post(`/syllabus/generate/${sessionId}?force=${force}`, { topic })

export const updateSyllabusItem = (itemDbId: number, status: string, masteryScore?: number) =>
    api.put(`/syllabus/item/${itemDbId}`, { status, mastery_score: masteryScore })

// ── 课堂 ─────────────────────────────────────────────
export const startLesson = (sessionId: number, itemDbId: number, reteach = false) =>
    api.post(`/classroom/start/${sessionId}`, { item_db_id: itemDbId, reteach })

export const askQuestion = (sessionId: number, conversationId: number, question: string) =>
    api.post(`/classroom/ask/${sessionId}`, { conversation_id: conversationId, question })

export const startQuiz = (sessionId: number, conversationId: number, itemDbId: number) =>
    api.post(`/classroom/start-quiz/${sessionId}`, { conversation_id: conversationId, item_db_id: itemDbId })

export const startQuizStream = (sessionId: number, conversationId: number, itemDbId: number, onChunk: (text: string) => void) =>
    fetchStream(`/classroom/start-quiz_stream/${sessionId}`, { conversation_id: conversationId, item_db_id: itemDbId }, onChunk)

export const saveQuizAnswers = (sessionId: number, quizId: number, answers: string[]) =>
    api.post(`/classroom/save_quiz_answers/${sessionId}`, { quiz_id: quizId, answers })

export const submitQuiz = (sessionId: number, quizId: number, itemDbId: number,
    answers: string[], images: File[] = []) => {
    const form = new FormData()
    form.append('quiz_id', String(quizId))
    form.append('item_db_id', String(itemDbId))
    form.append('answers', JSON.stringify(answers))
    images.forEach(img => form.append('images', img))
    return axios.post(
        `${BASE_URL}/classroom/submit-quiz/${sessionId}`,
        form, { timeout: 120000 }
    ).then(r => r.data)
}

// ── 考试 ─────────────────────────────────────────────
export const checkExamUnlock = (sessionId: number) =>
    api.get(`/exam/unlock-check/${sessionId}`)

export const generateExam = (sessionId: number, examType: 'midterm' | 'final') =>
    api.post(`/exam/generate/${sessionId}`, { exam_type: examType })

export const generateExamStream = (sessionId: number, examType: 'midterm' | 'final', onChunk: (text: string) => void) =>
    fetchStream(`/exam/generate_stream/${sessionId}`, { exam_type: examType }, onChunk)

export const submitExam = (sessionId: number, examId: number,
    answers: string[], images: File[] = []) => {
    const form = new FormData()
    form.append('exam_id', String(examId))
    form.append('answers', JSON.stringify(answers))
    images.forEach(img => form.append('images', img))
    return axios.post(
        `${import.meta.env.VITE_API_BASE_URL || '/api'}/exam/submit/${sessionId}`,
        form, { timeout: 120000 }
    ).then(r => r.data)
}

// ── 旧接口兼容 ─────────────────────────────────────────
export const quickTeach = (topic: string, question?: string) =>
    api.post('/learning/quick-teach', { topic, question })

export const generatePractice = (topic: string, difficulty = 'medium', count = 5) =>
    api.post('/learning/practice', { topic, difficulty, count })

export const getSyllabus = (topic: string) =>
    api.post('/learning/syllabus', { topic })

export const getStudents = () => api.get('/students')
