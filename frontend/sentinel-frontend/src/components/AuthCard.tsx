import React from 'react';

export default function AuthCard({ children }: { children: React.ReactNode }) {
  return (
    <div className="w-full max-w-[450px] bg-white/20 backdrop-blur-3xl p-10 rounded-[2.5rem] border border-white/30 shadow-2xl mx-auto mt-8">
      {children}
    </div>
  );
}