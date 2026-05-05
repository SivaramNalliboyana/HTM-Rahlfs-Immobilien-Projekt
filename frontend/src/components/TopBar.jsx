export default function TopBar() {
  return (
    <header className="w-full sticky top-0 z-40 border-b border-slate-200 bg-white flex justify-between items-center px-8 h-20">
      <div className="flex items-center gap-4 flex-1">
        <span className="material-symbols-outlined text-[#1a2b4a]">search</span>
        <input
          className="bg-transparent border-none focus:ring-0 text-body-md text-on-surface w-full max-w-md placeholder-slate-400 outline-none"
          placeholder="Search operations..."
          type="text"
        />
      </div>
      <div className="flex items-center gap-6">
        <div className="relative cursor-pointer text-slate-400 hover:text-[#1a2b4a] transition-colors">
          <span className="material-symbols-outlined">notifications</span>
          <span className="absolute -top-1 -right-1 bg-error text-white text-[10px] font-bold w-4 h-4 rounded-full flex items-center justify-center">
            3
          </span>
        </div>
        <button className="bg-primary-container text-white px-4 py-2 rounded-lg text-label-md hover:bg-primary transition-colors duration-200 shadow-sm flex items-center gap-2">
          <span className="material-symbols-outlined text-[18px]">add</span>
          New Case
        </button>
      </div>
    </header>
  )
}
