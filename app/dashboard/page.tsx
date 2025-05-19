'use client';

import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';

// 訊息型別：誰說的 + 內容
type Message = {
  role: 'user' | 'bot';
  content: string | React.ReactNode;
};

export default function DashboardPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement | null>(null);

  function addMessage(message: Message) {
    setMessages((prev) => [...prev, message]);
  }

  async function handleSubmit() {
    const userInput = input.trim();
    if (!userInput) return;

    addMessage({ role: 'user', content: userInput });
    setInput('');

    const loadingMsg: Message = { role: 'bot', content: '🤖 思考中...' };
    addMessage(loadingMsg);
    const loadingIndex = messages.length;

    try {
      const res = await fetch('http://127.0.0.1:8000/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_query: userInput }),
      });

      if (!res.ok) throw new Error('API 回應錯誤');
      const data = await res.json();

      const botText = data.output.extracted_content;
      const fileUrl = data.output.download_file_url;

      const finalText =
        botText + (fileUrl ? `\n\n📎 [點此開啟檔案](${fileUrl})` : '');

      setMessages((prev) => {
        const updated = [...prev];
        updated[loadingIndex + 1] = {
          role: 'bot',
          content: finalText,
        };
        return updated;
      });
    } catch (error: any) {
      setMessages((prev) => {
        const updated = [...prev];
        updated[loadingIndex + 1] = {
          role: 'bot',
          content: '⚠️ 發送失敗：' + error.message,
        };
        return updated;
      });
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="relative flex flex-col h-full bg-gray-50">
      {/* Chat messages */}
      <main className="flex-1 overflow-y-auto p-6 flex flex-col space-y-4">
        {messages.length === 0 ? (
          <div className="text-gray-400 text-center mt-10">尚無訊息</div>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`px-4 py-2 rounded-2xl shadow max-w-[75%] ${
                  msg.role === 'user'
                    ? 'bg-teal-500 text-white'
                    : 'bg-white border border-gray-300 text-gray-800'
                }`}
              >
                {msg.role === 'bot' ? (
                  <ReactMarkdown
                    components={{
                        a: ({ href, children }) => (
                        <a
                            href={href}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-800 underline font-semibold"
                        >
                            {children}
                        </a>
                        ),
                    }}
                    >
                        {msg.content as string}
                    </ReactMarkdown>
                ) : (
                  msg.content
                )}
              </div>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </main>

      {/* Floating buttons */}
      <div className="fixed bottom-36 right-6 flex flex-col gap-4 z-10">
        <div className="group relative">
          <div className="absolute right-full mr-2 top-1/2 -translate-y-1/2 bg-black text-white text-xs px-3 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
            添加文件進入機器人資料庫
          </div>
          <button className="w-14 h-14 rounded-full bg-teal-600 flex items-center justify-center shadow-lg hover:bg-teal-500 transition">
            <img
              src="https://cdn-icons-png.flaticon.com/512/337/337946.png"
              alt="PDF"
              className="w-7 h-7"
            />
          </button>
        </div>
        <div className="group relative">
          <div className="absolute right-full mr-2 top-1/2 -translate-y-1/2 bg-black text-white text-xs px-3 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
            教導機器人他不會的任務
          </div>
          <button className="w-14 h-14 rounded-full bg-teal-600 flex items-center justify-center shadow-lg hover:bg-teal-500 transition">
            <img
              src="https://cdn-icons-png.flaticon.com/512/4712/4712100.png"
              alt="Bot"
              className="w-7 h-7"
            />
          </button>
        </div>
      </div>

      {/* Input + Send */}
      <div className="border-t bg-white p-4">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            type="text"
            placeholder="輸入你的訊息..."
            className="flex-1 p-3 border border-teal-500 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
          />
          <button
            onClick={handleSubmit}
            className="px-5 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-500 transition"
          >
            送出
          </button>
        </div>
      </div>
    </div>
  );
}
