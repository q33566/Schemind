'use client';

import {
  ChatBubbleBottomCenterTextIcon,
  UserGroupIcon,
} from '@heroicons/react/24/outline';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import clsx from 'clsx';

// 自訂導航清單
const links = [
  {
    name: '聊天介面',
    href: '/dashboard',
    icon: ChatBubbleBottomCenterTextIcon,
  },
  {
    name: '管理聯絡人',
    href: '/dashboard/contacts',
    icon: UserGroupIcon,
  },
];

export default function NavLinks() {
  const pathname = usePathname();

  return (
    <>
      {links.map((link) => {
        const LinkIcon = link.icon;

        const isActive =
          pathname === link.href || pathname.startsWith(link.href + '/');

        return (
          <Link
            key={link.name}
            href={link.href}
            className={clsx(
              'flex h-[48px] grow items-center justify-center gap-2 rounded-md bg-gray-50 p-3 text-sm font-medium transition-colors hover:bg-teal-100 hover:text-teal-700 md:justify-start md:p-2 md:px-3',
              {
                'bg-teal-100 text-teal-700': isActive,
              }
            )}
          >
            <LinkIcon className="w-6" />
            <span className="hidden md:block">{link.name}</span>
          </Link>
        );
      })}
    </>
  );
}
