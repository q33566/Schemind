'use client';

import Link from 'next/link';
import NavLinks from '@/app/ui/dashboard/nav-links';
import { PowerIcon } from '@heroicons/react/24/outline';

export default function SideNav() {
  return (
    <div className="flex h-full flex-col px-3 py-4 md:px-2 bg-white border-r">
      {/* 頂部 Logo / 標題 */}
      <Link
        className="mb-2 flex h-20 items-end justify-start rounded-md bg-teal-600 p-4 md:h-32"
        href="/"
      >
        <div className="text-white text-xl font-bold">Schemind</div>
      </Link>

      {/* 導覽連結區域 */}
      <div className="flex grow flex-row justify-between md:flex-col md:space-y-2">
        <NavLinks />
      </div>
    </div>
  );
}
