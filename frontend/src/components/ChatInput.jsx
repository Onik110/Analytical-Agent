export default function ChatInput({ input, setInput, handleSend, isLoading }) {
    return (
        <div className="chat-input-container" style={{ display: 'flex', gap: '12px' }}>
            <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Введите ваш вопрос о данных производства..."
                disabled={isLoading}
                rows="3"
                style={{
                    flex: 1,
                    padding: '16px',
                    border: '2px solid #e9ecef',
                    borderRadius: '16px',
                    fontSize: '1rem',
                    resize: 'vertical',
                    minHeight: '60px',
                    maxHeight: '120px',
                    transition: 'border-color 0.3s'
                }}
                onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        handleSend()
                    }
                }}
            />
            <button
                onClick={handleSend}
                disabled={isLoading || !input.trim()}
                style={{
                    width: '56px',
                    height: '56px',
                    background: 'linear-gradient(135deg, #4361ee, #3a56d4)',
                    color: 'white',
                    border: 'none',
                    borderRadius: '16px',
                    fontSize: '1.4rem',
                    cursor: isLoading ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'all 0.3s',
                    flexShrink: 0,
                    boxShadow: '0 4px 12px rgba(67, 97, 238, 0.3)'
                }}
                aria-label="Отправить запрос"
            >
                {isLoading ? (
                    <div style={{
                        width: '24px',
                        height: '24px',
                        border: '3px solid rgba(255, 255, 255, 0.3)',
                        borderTop: '3px solid white',
                        borderRadius: '50%',
                        animation: 'spin 1s linear infinite'
                    }}></div>
                ) : (
                    <span>➤</span>
                )}
            </button>
        </div>
    )
}