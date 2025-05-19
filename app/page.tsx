'use client';

import { ArrowRightIcon } from '@heroicons/react/24/outline';
import Link from 'next/link';
import { lusitana } from '@/app/ui/fonts';

export default function Page() {
  return (
    <main className="flex min-h-screen flex-col p-6">
      {/* 頂部標題區塊 */}
      <div className="flex h-20 shrink-0 items-end rounded-lg bg-teal-600 p-4 md:h-52">
        <h1 className="text-white text-xl md:text-3xl font-bold">Schemind Chat</h1>
      </div>

      {/* 主內容 */}
      <div className="mt-4 flex grow flex-col gap-4 md:flex-row">
        {/* 左側介紹與導覽按鈕 */}
        <div className="flex flex-col justify-center gap-6 rounded-lg bg-gray-50 px-6 py-10 md:w-2/5 md:px-20">
          <p
            className={`${lusitana.className} text-xl text-gray-800 md:text-3xl md:leading-normal`}
          >
            歡迎使用 <strong>Schemind 智能對話平台</strong>。
          </p>

          {/* 主按鈕：跳到聯絡人管理或聊天主頁 */}
          <Link
            href="/dashboard"
            className="flex items-center gap-5 self-start rounded-lg bg-teal-600 px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-teal-500 md:text-base"
          >
            <span>開始聊天</span>
            <ArrowRightIcon className="w-5 md:w-6" />
          </Link>
        </div>

        {/* 右側可放圖片或動畫 */}
        <div className="flex items-center justify-center p-6 md:w-3/5 md:px-28 md:py-12">
          <p className="text-gray-400"></p>
        </div>
      </div>
    </main>
  );
}
