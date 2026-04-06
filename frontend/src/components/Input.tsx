import React from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
}

export default function Input({ label, ...props }: InputProps) {
  return (
    <div className="w-full flex flex-col gap-2">
      <label className="text-[10px] uppercase tracking-widest font-bold text-brand-deep/50 ml-2">
        {label}
      </label>
      <input
        {...props}
        className="w-full px-6 py-4 bg-white/40 backdrop-blur-md rounded-2xl border border-white/40 text-brand-deep placeholder:text-brand-deep/30 focus:outline-none focus:ring-2 focus:ring-brand-accent/50 transition-all"
      />
    </div>
  );
}