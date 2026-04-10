export default function ChatMessage({ message }) {
    const formatTimestamp = (date) => {
        if (!date) return ''
        const d = date instanceof Date ? date : new Date(date)
        return d.toLocaleTimeString('ru-RU', {
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
        })
    }

    const renderContent = (content) => {
        if (!content) return null
        
        return content
            .split('\n')
            .map((line, i) => {
                line = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                line = line.replace(/`([^`]+)`/g, '<code style="background:#f1f3f4;padding:2px 6px;border-radius:4px;font-family:monospace">$1</code>')
                return <div key={i} dangerouslySetInnerHTML={{ __html: line || '<br/>' }} />
            })
    }

    return (
        <div className={`message ${message.role}`} style={{ maxWidth: message.role === 'system' ? '90%' : '85%' }}>
            {message.role === 'system' ? (
                <div className="system-content" style={{ textAlign: 'center', fontStyle: 'italic' }}>
                    {renderContent(message.content)}
                </div>
            ) : (
                <div className="message-content">
                    {renderContent(message.content)}
                </div>
            )}

            {message.attempts > 0 && (
                <div className="attempts-info">
                    <span>🔄</span>
                    <span>Попыток исправления: {message.attempts}/5</span>
                </div>
            )}

            {message.query && (
                <div className="query-block" style={{ 
                    marginTop: '12px', 
                    padding: '12px', 
                    background: '#f8f9fa', 
                    borderRadius: '8px',
                    border: '1px solid #e9ecef'
                }}>
                    <div className="query-header" style={{ 
                        fontSize: '0.85rem', 
                        fontWeight: '600', 
                        marginBottom: '8px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px'
                    }}>
                        <span>🔍 Сгенерированный запрос 1С:</span>
                        {message.anonymized && (
                            <span className="anonymized-tag" style={{ 
                                background: 'rgba(6, 214, 160, 0.2)', 
                                color: '#05a677',
                                padding: '2px 8px',
                                borderRadius: '12px',
                                fontSize: '0.75rem'
                            }}>
                                Анонимизирован
                            </span>
                        )}
                    </div>
                    <pre className="query-content" style={{ 
                        fontSize: '0.8rem', 
                        overflowX: 'auto',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        margin: 0,
                        padding: '8px',
                        background: 'white',
                        borderRadius: '4px'
                    }}>
                        {message.query}
                    </pre>
                </div>
            )}

            {message.table && (
                <div className="table-result" style={{ marginTop: '12px' }} dangerouslySetInnerHTML={{ __html: message.table }} />
            )}

            {message.htmlInsight && (
                <div className="insight-result" style={{ marginTop: '12px' }} dangerouslySetInnerHTML={{ __html: message.htmlInsight }} />
            )}

            {message.fileInfo && (
                <div className="file-info" style={{ 
                    marginTop: '12px',
                    padding: '10px 14px',
                    background: 'rgba(67, 97, 238, 0.1)',
                    border: '1px solid rgba(67, 97, 238, 0.3)',
                    borderRadius: '8px',
                    fontSize: '0.85rem',
                    color: '#4361ee'
                }}>
                    💾 Сохранено: <strong>{message.fileInfo.file_id}</strong> ({message.fileInfo.anonymized_rows} строк)
                </div>
            )}

            <div className="timestamp">
                {formatTimestamp(message.timestamp)}
            </div>
        </div>
    )
}