'use client';

import { useEffect, useState } from 'react';

type Contact = {
  name: string;
  description: string;
  email: string;
};

export default function ContactManagerPage() {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [formData, setFormData] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');

  // 讀取聯絡人列表
  async function fetchContacts() {
    const res = await fetch('http://127.0.0.1:8000/contacts');
    const data = await res.json();
    setContacts(data);
    setFormData(data); // 預設表單填入現有值
  }

  // 更新表單欄位內容
  function handleChange(index: number, field: keyof Contact, value: string) {
    const newData = [...formData];
    newData[index][field] = value;
    setFormData(newData);
  }

  // 新增一筆空的聯絡人欄位
  function addRow() {
    setFormData([...formData, { name: '', description: '', email: '' }]);
  }

  // 刪除聯絡人
  async function handleDelete(name: string) {
    const confirmed = confirm(`確定要刪除聯絡人「${name}」嗎？`);
    if (!confirmed) return;

    const res = await fetch(`http://127.0.0.1:8000/contacts/${encodeURIComponent(name)}`, {
      method: 'DELETE',
    });

    if (res.ok) {
      setSuccessMsg(`🗑️ 已刪除聯絡人 ${name}`);
      await fetchContacts();
    } else {
      alert('❌ 刪除失敗');
    }
  }

  // 提交表單
  async function handleSubmit() {
    setLoading(true);
    const res = await fetch('http://127.0.0.1:8000/update_contacts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contacts: formData }),
    });

    if (res.ok) {
      setSuccessMsg('✅ 聯絡人更新成功');
      await fetchContacts();
    } else {
      alert('❌ 更新失敗');
    }

    setLoading(false);
  }

  useEffect(() => {
    fetchContacts();
  }, []);

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-gray-700">管理聯絡人</h1>

      <table className="w-full border text-left">
        <thead className="bg-gray-100 text-sm">
          <tr>
            <th className="p-2 border">名稱</th>
            <th className="p-2 border">描述</th>
            <th className="p-2 border">Email</th>
            <th className="p-2 border">操作</th>
          </tr>
        </thead>
        <tbody>
          {formData.map((c, i) => (
            <tr key={i}>
              <td className="p-2 border">
                <input
                  className="w-full border px-2 py-1"
                  value={c.name}
                  onChange={(e) => handleChange(i, 'name', e.target.value)}
                />
              </td>
              <td className="p-2 border">
                <input
                  className="w-full border px-2 py-1"
                  value={c.description}
                  onChange={(e) => handleChange(i, 'description', e.target.value)}
                />
              </td>
              <td className="p-2 border">
                <input
                  className="w-full border px-2 py-1"
                  value={c.email}
                  onChange={(e) => handleChange(i, 'email', e.target.value)}
                />
              </td>
              <td className="p-2 border text-center">
                <button
                  onClick={() => handleDelete(c.name)}
                  className="text-red-600 hover:underline"
                >
                  刪除
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="flex gap-4">
        <button
          onClick={addRow}
          className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
        >
          ➕ 新增聯絡人
        </button>

        <button
          onClick={handleSubmit}
          disabled={loading}
          className="px-6 py-2 bg-teal-600 text-white rounded hover:bg-teal-500"
        >
          {loading ? '更新中...' : '💾 更新'}
        </button>
      </div>

      {successMsg && <p className="text-green-600">{successMsg}</p>}
    </div>
  );
}
