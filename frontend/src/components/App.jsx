import { useState, useEffect, useRef } from 'react'
import './App.css'
import ChatMessage from './ChatMessage'
import ChatInput from './ChatInput'
import FileBrowser from './FileBrowser'

function App() {
    const [messages, setMessages] = useState([
        {
            id: 1,
            role: 'bot',
            content: 'Здравствуйте! Я помогу вам анализировать данные производства из 1С. Задайте вопрос на естественном языке.',
            timestamp: new Date()
        }
    ])
    const [input, setInput] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [connectionStatus, setConnectionStatus] = useState('idle')
    const [files, setFiles] = useState([])
    const [selectedFile, setSelectedFile] = useState(null)
    const [isAnalyzing, setIsAnalyzing] = useState(false)
    const chatRef = useRef(null)

    useEffect(() => {
        if (chatRef.current) {
            chatRef.current.scrollTop = chatRef.current.scrollHeight
        }
    }, [messages])

    useEffect(() => {
        checkConnection()
        loadFiles()
    }, [])

    const checkConnection = async () => {
        try {
            const res = await fetch('/api/health')
            const data = await res.json()
            setConnectionStatus(data.com_connected && data.llm_connected ? 'connected' : 'idle')
        } catch (e) {
            setConnectionStatus('error')
        }
    }

    const loadFiles = async () => {
        try {
            const res = await fetch('/api/insights/files')
            const data = await res.json()
            setFiles(data.files || [])
        } catch (e) {
            console.error('Ошибка загрузки файлов:', e)
        }
    }

    const analyzeFile = async (fileId, prompt = null) => {
        if (!fileId || typeof fileId !== 'string') {
            setMessages(prev => [...prev, {
                id: Date.now() + Math.random(),
                role: 'error',
                content: 'Ошибка: неверный идентификатор файла',
                timestamp: new Date()
            }])
            return
        }
        setIsAnalyzing(true)
        try {
            const body = { file_id: fileId }
            if (prompt) body.prompt = prompt

            const response = await fetch('/api/insights/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            })

            if (!response.ok) {
                const errorData = await response.json().catch(() => null)
                throw new Error(`Ошибка ${response.status}: ${errorData?.error || errorData?.detail || response.statusText}`)
            }

            const data = await response.json()

            if (data.success) {
                setMessages(prev => [...prev, {
                    id: Date.now() + Math.random(),
                    role: 'bot',
                    content: `**Авто-анализ файла ${fileId}**\n\n${data.insight}`,
                    timestamp: new Date()
                }])
            } else {
                setMessages(prev => [...prev, {
                    id: Date.now() + Math.random(),
                    role: 'error',
                    content: `Ошибка анализа: ${data.error || 'Неизвестная ошибка'}`,
                    timestamp: new Date()
                }])
            }
        } catch (error) {
            console.error('Ошибка анализа:', error)
            setMessages(prev => [...prev, {
                id: Date.now() + Math.random(),
                role: 'error',
                content: `Ошибка: ${error.message || 'Не удалось проанализировать файл'}`,
                timestamp: new Date()
            }])
        } finally {
            setIsAnalyzing(false)
        }
    }

    const handleSend = async () => {
        const trimmedInput = input.trim()
        if (!trimmedInput) {
            setMessages(prev => [...prev, {
                id: Date.now() + Math.random(),
                role: 'system',
                content: 'Запрос не может быть пустым. Введите ваш вопрос.',
                timestamp: new Date()
            }])
            return
        }
        if (trimmedInput.length < 3) {
            setMessages(prev => [...prev, {
                id: Date.now() + Math.random(),
                role: 'system',
                content: 'Запрос слишком короткий. Опишите, что вы хотите узнать.',
                timestamp: new Date()
            }])
            return
        }

        const userMessage = {
            id: Date.now(),
            role: 'user',
            content: trimmedInput,
            timestamp: new Date()
        }
        setMessages(prev => [...prev, userMessage])
        setInput('')
        setIsLoading(true)

        if (connectionStatus !== 'connected') {
            setMessages(prev => [...prev, {
                id: 'connecting',
                role: 'system',
                content: 'Устанавливаю соединение с 1С...\n⏳ Первое подключение может занять до 3 минут (зависит от скорости сети)',
                timestamp: new Date()
            }])
            setConnectionStatus('connecting')
        }

        try {
            const controller = new AbortController()
            const timeoutId = setTimeout(() => controller.abort(), 180000)

            const response = await fetch('/api/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: trimmedInput, save: true }),
                signal: controller.signal
            })

            clearTimeout(timeoutId)
            setMessages(prev => prev.filter(msg => msg.id !== 'connecting'))

            if (!response.ok) {
                throw new Error(`Сервер вернул статус ${response.status}`)
            }

            const data = await response.json()

            if (data.success) {
                setConnectionStatus('connected')

                if (data.file_info) {
                    loadFiles()
                }

                const botMessage = {
                    id: Date.now() + 1,
                    role: 'bot',
                    content: data.summary || 'Запрос выполнен успешно',
                    table: data.result_table,
                    query: data.query_1c,
                    attempts: data.fix_attempts,
                    anonymized: data.anonymized,
                    fileInfo: data.file_info,
                    timestamp: new Date()
                }
                setMessages(prev => [...prev, botMessage])

                if (data.file_info) {
                    setMessages(prev => [...prev, {
                        id: Date.now() + 2,
                        role: 'system',
                        content: `Данные сохранены в файл: **${data.file_info.file_id}**\n📁 Доступно для анализа в правой панели`,
                        timestamp: new Date()
                    }])
                }
            } else {
                const errorMessage = {
                    id: Date.now() + 1,
                    role: 'error',
                    content: data.error || 'Неизвестная ошибка выполнения запроса',
                    attempts: data.fix_attempts,
                    timestamp: new Date()
                }
                setMessages(prev => [...prev, errorMessage])
            }

        } catch (error) {
            console.error('Ошибка запроса:', error)
            setMessages(prev => prev.filter(msg => msg.id !== 'connecting'))

            let errorMessage = 'Неизвестная ошибка'

            if (error.name === 'AbortError') {
                errorMessage = 'Превышено время ожидания ответа от 1С.\nПервое подключение может занять до 60 секунд. Повторите запрос через 20 секунд.'
            } else if (error.message.includes('Failed to fetch')) {
                errorMessage = 'Нет связи с сервером.\nПроверьте, запущен ли бэкенд на порту 8000.'
            } else {
                errorMessage = `Ошибка: ${error.message || 'Неизвестная ошибка'}`
            }

            setMessages(prev => [...prev, {
                id: Date.now() + 1,
                role: 'error',
                content: errorMessage,
                timestamp: new Date()
            }])
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="app-container">
            <header className="app-header">
                <div className="header-content">
                    <h1 className="app-title">1С Ассистент</h1>
                    <p className="app-subtitle">Анализ данных производства с защитой персональных данных</p>
                </div>
                <div className="status-bar">
                    {connectionStatus === 'idle' && (
                        <span className="status-badge idle" onClick={checkConnection}>
                            ⚪ Ожидание подключения
                        </span>
                    )}
                    {connectionStatus === 'connecting' && (
                        <span className="status-badge connecting">
                            <span className="pulse"></span> Подключение к 1С...
                        </span>
                    )}
                    {connectionStatus === 'connected' && (
                        <span className="status-badge connected">
                            <span className="status-icon">🟢</span> Подключено к 1С
                        </span>
                    )}
                    {connectionStatus === 'error' && (
                        <span className="status-badge error" onClick={checkConnection}>
                            🔴 Ошибка подключения (кликните для повтора)
                        </span>
                    )}

                    <span className="anonymization-badge enabled" title="Все персональные данные анонимизированы">
                        🔒 Анонимизация ВКЛ
                    </span>
                </div>
            </header>

            <main className="app-main">
                <div className="chat-container">
                    <div className="chat-messages" ref={chatRef}>
                        {messages.map((message) => (
                            <ChatMessage key={message.id} message={message} />
                        ))}

                        {isLoading && connectionStatus === 'connected' && (
                            <div className="message bot loading">
                                <div className="loading-content">
                                    <div className="loading-dots">
                                        <span></span><span></span><span></span>
                                    </div>
                                    <div>Думаю над вашим запросом...</div>
                                </div>
                            </div>
                        )}
                    </div>

                    <div className="result-panel">
                        <FileBrowser
                            files={files}
                            selectedFile={selectedFile}
                            onSelectFile={setSelectedFile}
                            onAnalyze={analyzeFile}
                            isAnalyzing={isAnalyzing}
                        />
                    </div>
                </div>

                <div className="input-container">
                    <ChatInput
                        input={input}
                        setInput={setInput}
                        handleSend={handleSend}
                        isLoading={isLoading}
                    />

                    <div className="input-hint">
                        Примеры запросов:
                        <span
                            className="example-query"
                            onClick={() => setInput('Покажи всех ткачей за сентябрь 2024')}
                        >
                            "Покажи всех ткачей за сентябрь 2024"
                        </span>
                        ,
                        <span
                            className="example-query"
                            onClick={() => setInput('Какой терминал простаивал больше всех?')}
                        >
                            "Какой терминал простаивал больше всех?"
                        </span>
                        <br />
                        <strong>Все персональные данные автоматически анонимизируются</strong> (ФИО → "Ткач #1", терминалы → "Терминал #1")
                    </div>
                </div>
            </main>

            <footer className="app-footer">
                <div className="footer-content">
                    <p>© 2026 1С Ассистент. Все персональные данные защищены в соответствии с ФЗ-152</p>
                </div>
            </footer>
        </div>
    )
}

export default App
