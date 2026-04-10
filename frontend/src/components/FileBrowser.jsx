import { useState } from 'react'

export default function FileBrowser({ 
  files, 
  selectedFile,   
  onSelectFile,   
  onAnalyze, 
  isAnalyzing 
}) {
    const [searchQuery, setSearchQuery] = useState('')
    
    const filteredFiles = files.filter(f => 
        f.query?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        f.file_id?.toLowerCase().includes(searchQuery.toLowerCase())
    )
    
    const handleFileSelect = (file) => {
        onSelectFile(file)  
    }
    
    const handleAnalyze = () => {
        if (selectedFile && onAnalyze) {
            onAnalyze(selectedFile.file_id)  
        }
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '0 8px' }}>
            <h3 style={{
                fontSize: '1.3rem',
                marginBottom: '16px',
                color: '#212529',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
            }}>
                📁 Файлы для анализа
            </h3>

            <input
                type="text"
                placeholder="🔍 Поиск по названию или запросу..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                    padding: '10px 14px',
                    border: '2px solid #e9ecef',
                    borderRadius: '10px',
                    marginBottom: '12px',
                    fontSize: '0.9rem',
                    width: '100%',
                    boxSizing: 'border-box',
                    transition: 'border-color 0.2s'
                }}
                onFocus={(e) => e.target.style.borderColor = '#4361ee'}
                onBlur={(e) => e.target.style.borderColor = '#e9ecef'}
            />

            <div style={{
                flex: 1,
                overflowY: 'auto',
                marginBottom: '16px',
                paddingRight: '4px'
            }}>
                {filteredFiles.length === 0 ? (
                    <div style={{
                        textAlign: 'center',
                        color: '#6c757d',
                        padding: '30px 16px',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        gap: '12px'
                    }}>
                        <div style={{ fontSize: '2.5rem', opacity: 0.7 }}>📭</div>
                        <p style={{ fontSize: '0.95rem', fontWeight: '500' }}>Нет сохранённых файлов</p>
                        <p style={{ fontSize: '0.85rem', maxWidth: '280px', lineHeight: 1.4 }}>
                            Отправьте запрос в чат и данные автоматически сохранятся для анализа
                        </p>
                    </div>
                ) : (
                    filteredFiles.map(file => (
                        <div
                            key={file.file_id}
                            onClick={() => handleFileSelect(file)}
                            style={{
                                padding: '12px 14px',
                                border: `2px solid ${selectedFile?.file_id === file.file_id ? '#4361ee' : '#e9ecef'}`,
                                borderRadius: '10px',
                                marginBottom: '8px',
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                                background: selectedFile?.file_id === file.file_id ? 'rgba(67, 97, 238, 0.05)' : 'white',
                                display: 'flex',
                                flexDirection: 'column',
                                gap: '4px'
                            }}
                            onMouseEnter={(e) => {
                                if (selectedFile?.file_id !== file.file_id) {
                                    e.currentTarget.style.borderColor = '#4361ee'
                                    e.currentTarget.style.background = 'rgba(67, 97, 238, 0.03)'
                                }
                            }}
                            onMouseLeave={(e) => {
                                if (selectedFile?.file_id !== file.file_id) {
                                    e.currentTarget.style.borderColor = '#e9ecef'
                                    e.currentTarget.style.background = 'white'
                                }
                            }}
                        >
                            <div style={{
                                fontWeight: '600',
                                fontSize: '0.95rem',
                                color: '#212529',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px'
                            }}>
                                📄 {file.file_id?.replace('query_', '')}
                            </div>
                            <div style={{
                                fontSize: '0.8rem',
                                color: '#6c757d',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap'
                            }}>
                                {file.query || 'Без названия'}
                            </div>
                            <div style={{
                                fontSize: '0.75rem',
                                color: '#adb5bd',
                                display: 'flex',
                                justifyContent: 'space-between'
                            }}>
                                <span>📊 {file.rows || 0} строк</span>
                                <span>{file.timestamp ? new Date(file.timestamp).toLocaleDateString('ru-RU') : ''}</span>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {selectedFile && (
                <div style={{
                    borderTop: '1px solid #e9ecef',
                    paddingTop: '16px',
                    marginTop: 'auto'
                }}>
                    <div style={{
                        fontSize: '0.9rem',
                        fontWeight: '500',
                        marginBottom: '12px',
                        color: '#212529',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px'
                    }}>
                        ✅ Выбран: <span style={{ color: '#4361ee' }}>{selectedFile.file_id?.replace('query_', '')}</span>
                    </div>

                    <button
                        onClick={handleAnalyze}
                        disabled={isAnalyzing}
                        style={{
                            width: '100%',
                            padding: '12px 16px',
                            background: isAnalyzing
                                ? 'linear-gradient(135deg, #6c757d, #5a6268)'
                                : 'linear-gradient(135deg, #4361ee, #3a56d4)',
                            color: 'white',
                            border: 'none',
                            borderRadius: '10px',
                            fontSize: '0.95rem',
                            fontWeight: '600',
                            cursor: isAnalyzing ? 'not-allowed' : 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '8px',
                            transition: 'all 0.2s',
                            boxShadow: isAnalyzing ? 'none' : '0 4px 12px rgba(67, 97, 238, 0.3)'
                        }}
                        onMouseEnter={(e) => {
                            if (!isAnalyzing) {
                                e.target.style.transform = 'translateY(-2px)'
                                e.target.style.boxShadow = '0 6px 16px rgba(67, 97, 238, 0.4)'
                            }
                        }}
                        onMouseLeave={(e) => {
                            if (!isAnalyzing) {
                                e.target.style.transform = 'translateY(0)'
                                e.target.style.boxShadow = '0 4px 12px rgba(67, 97, 238, 0.3)'
                            }
                        }}
                    >
                        {isAnalyzing ? (
                            <>
                                <div style={{
                                    width: '18px', height: '18px',
                                    border: '2px solid rgba(255,255,255,0.3)',
                                    borderTop: '2px solid white',
                                    borderRadius: '50%',
                                    animation: 'spin 1s linear infinite'
                                }}></div>
                                Анализирую...
                            </>
                        ) : (
                            <>Запустить авто-анализ</>
                        )}
                    </button>

                    <p style={{
                        fontSize: '0.75rem',
                        color: '#6c757d',
                        marginTop: '10px',
                        textAlign: 'center',
                        lineHeight: 1.4
                    }}>
                        🔒 Анализ выполняется на анонимизированных данных
                    </p>
                </div>
            )}
        </div>
    )
}