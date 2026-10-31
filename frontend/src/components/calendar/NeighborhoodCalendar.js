'use client';

import React, { useState } from 'react';
import {
  Calendar as CalendarIcon,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  MapPin,
  Clock,
  AlertCircle,
  Sparkles,
  ArrowRight,
  ShieldAlert
} from 'lucide-react';

export default function NeighborhoodCalendar({
  events = [],
  selectedEventId = null,
  onSelectEvent = null,
}) {
  // Calendar base state (Defaulting to November 2026 based on seed events)
  const [currentYear, setCurrentYear] = useState(2026);
  const [currentMonth, setCurrentMonth] = useState(10); // 0-indexed: 10 = November
  const [selectedDay, setSelectedDay] = useState(null);

  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];

  const handlePrevMonth = () => {
    if (currentMonth === 0) {
      setCurrentMonth(11);
      setCurrentYear((y) => y - 1);
    } else {
      setCurrentMonth((m) => m - 1);
    }
    setSelectedDay(null);
  };

  const handleNextMonth = () => {
    if (currentMonth === 11) {
      setCurrentMonth(0);
      setCurrentYear((y) => y + 1);
    } else {
      setCurrentMonth((m) => m + 1);
    }
    setSelectedDay(null);
  };

  // Generate calendar grid days for current month
  const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
  const firstDayIndex = new Date(currentYear, currentMonth, 1).getDay();

  // Helper to check if event occurs on a day
  const getEventsForDay = (dayNum) => {
    const formattedDayStr = `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}-${String(dayNum).padStart(2, '0')}`;
    return events.filter((ev) => {
      if (!ev.start_date) return false;
      const start = ev.start_date;
      const end = ev.end_date || ev.start_date;
      return formattedDayStr >= start && formattedDayStr <= end;
    });
  };

  // Filtered event list
  const displayedEvents = selectedDay
    ? getEventsForDay(selectedDay)
    : events;

  return (
    <div className="bg-white rounded-[28px] border border-stone-200/90 shadow-[0_4px_24px_rgba(20,24,20,0.04)] p-5 md:p-6 flex flex-col space-y-5">
      {/* Calendar Header with Month Navigation */}
      <div className="flex items-center justify-between pb-3 border-b border-stone-100">
        <div>
          <h3 className="text-base font-extrabold text-[#16181a] tracking-tight flex items-center gap-2">
            <CalendarIcon className="w-4 h-4 text-[#16181a]" />
            <span>Retail Demand Calendar</span>
          </h3>
          <p className="text-[11px] text-stone-500 font-medium mt-0.5">
            Festivals, community markets, and neighborhood footfall drivers
          </p>
        </div>

        <div className="flex items-center gap-1.5 bg-[#f7f8f4] border border-stone-200/90 rounded-full px-2 py-1 shadow-2xs">
          <button
            onClick={handlePrevMonth}
            className="w-7 h-7 rounded-full flex items-center justify-center hover:bg-stone-200/70 text-stone-700 transition-colors cursor-pointer"
            title="Previous month"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
          <span className="text-xs font-bold text-[#16181a] px-2 min-w-[110px] text-center">
            {monthNames[currentMonth]} {currentYear}
          </span>
          <button
            onClick={handleNextMonth}
            className="w-7 h-7 rounded-full flex items-center justify-center hover:bg-stone-200/70 text-stone-700 transition-colors cursor-pointer"
            title="Next month"
          >
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* 7-Day Week Header */}
      <div className="grid grid-cols-7 gap-1 text-center text-[10px] font-bold text-stone-400 uppercase tracking-wider">
        <span>Sun</span>
        <span>Mon</span>
        <span>Tue</span>
        <span>Wed</span>
        <span>Thu</span>
        <span>Fri</span>
        <span>Sat</span>
      </div>

      {/* Calendar Days Grid */}
      <div className="grid grid-cols-7 gap-1">
        {/* Empty padding days */}
        {Array.from({ length: firstDayIndex }).map((_, i) => (
          <div key={`empty-${i}`} className="h-10 rounded-xl" />
        ))}

        {/* Days of current month */}
        {Array.from({ length: daysInMonth }).map((_, i) => {
          const dayNum = i + 1;
          const dayEvents = getEventsForDay(dayNum);
          const hasEvents = dayEvents.length > 0;
          const isSelected = selectedDay === dayNum;
          const hasHighSeverity = dayEvents.some((e) => e.severity === 'HIGH');

          return (
            <button
              key={`day-${dayNum}`}
              onClick={() => setSelectedDay(isSelected ? null : dayNum)}
              className={`h-11 rounded-2xl flex flex-col items-center justify-center transition-all cursor-pointer relative ${
                isSelected
                  ? 'bg-[#16181a] text-white shadow-xs font-extrabold'
                  : hasEvents
                  ? 'bg-[#f7f8f4] hover:bg-stone-100 text-[#16181a] font-bold border border-stone-200/80'
                  : 'hover:bg-stone-50 text-stone-600'
              }`}
            >
              <span className="text-xs">{dayNum}</span>
              {hasEvents && (
                <div className="flex items-center gap-0.5 mt-0.5">
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      isSelected
                        ? 'bg-[#e0fd53]'
                        : hasHighSeverity
                        ? 'bg-[#c25e4e]'
                        : 'bg-[#16181a]'
                    }`}
                  />
                  {dayEvents.length > 1 && (
                    <span
                      className={`text-[8px] font-bold ${
                        isSelected ? 'text-[#e0fd53]' : 'text-stone-500'
                      }`}
                    >
                      {dayEvents.length}
                    </span>
                  )}
                </div>
              )}
            </button>
          );
        })}
      </div>

      {/* Selected Day Filter Badge */}
      {selectedDay && (
        <div className="flex items-center justify-between px-3 py-1.5 rounded-full bg-[#f7f8f4] border border-stone-200/90 text-xs">
          <span className="font-semibold text-stone-700">
            Filtering events for {monthNames[currentMonth]} {selectedDay}, {currentYear}
          </span>
          <button
            onClick={() => setSelectedDay(null)}
            className="text-[11px] font-bold text-[#16181a] hover:underline cursor-pointer"
          >
            Show All Events
          </button>
        </div>
      )}

      {/* Event Cards Stream */}
      <div className="space-y-3 pt-2">
        <div className="flex items-center justify-between text-xs font-bold text-stone-500 uppercase tracking-widest px-1">
          <span>Local Area Events ({displayedEvents.length})</span>
          <span className="text-[11px] text-stone-400 font-normal">Click event to focus on map</span>
        </div>

        {displayedEvents.length === 0 ? (
          <div className="p-8 text-center rounded-2xl bg-[#fbfbf9] border border-dashed border-stone-200">
            <CalendarIcon className="w-6 h-6 text-stone-300 mx-auto mb-2" />
            <p className="text-xs text-stone-500 font-medium">No major retail demand events scheduled for this day.</p>
          </div>
        ) : (
          displayedEvents.map((ev) => {
            const isSelected = selectedEventId === ev.event_id;
            return (
              <div
                key={ev.event_id}
                onClick={() => onSelectEvent && onSelectEvent(ev.event_id)}
                className={`p-4 rounded-2xl border transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-[#16181a] text-white border-stone-800 shadow-md ring-2 ring-[#e0fd53]/40'
                    : 'bg-white hover:bg-[#fafaf7] border-stone-200/90 text-stone-800 shadow-2xs'
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-[10px] font-black uppercase px-2.5 py-0.5 rounded-full ${
                        ev.severity === 'HIGH'
                          ? isSelected
                            ? 'bg-[#e0fd53] text-[#16181a]'
                            : 'bg-[#fbe8e4] text-[#a43b27] border border-[#f3c5bd]'
                          : isSelected
                          ? 'bg-stone-700 text-stone-200'
                          : 'bg-[#fbf4e6] text-[#8c5208] border border-[#f3ddb6]'
                      }`}
                    >
                      {ev.severity} IMPACT
                    </span>
                    <span
                      className={`text-xs font-bold ${
                        isSelected ? 'text-stone-300' : 'text-stone-500'
                      }`}
                    >
                      {ev.start_date === ev.end_date ? ev.start_date : `${ev.start_date} → ${ev.end_date}`}
                    </span>
                  </div>

                  {ev.distance_km !== null && (
                    <span
                      className={`text-[11px] font-mono font-bold ${
                        isSelected ? 'text-[#e0fd53]' : 'text-stone-500'
                      }`}
                    >
                      {ev.distance_km < 1 ? `${Math.round(ev.distance_km * 1000)}m away` : `${ev.distance_km} km away`}
                    </span>
                  )}
                </div>

                <h4
                  className={`text-sm font-extrabold tracking-tight mb-1 ${
                    isSelected ? 'text-white' : 'text-[#16181a]'
                  }`}
                >
                  {ev.title}
                </h4>

                <p
                  className={`text-xs leading-relaxed mb-3 ${
                    isSelected ? 'text-stone-300' : 'text-stone-600'
                  }`}
                >
                  {ev.description}
                </p>

                {/* Category Demand Multipliers */}
                <div className="flex flex-wrap items-center gap-1.5 mb-3">
                  {ev.category_impacts?.map((imp, idx) => (
                    <span
                      key={idx}
                      className={`text-[10.5px] px-2.5 py-1 rounded-full font-bold flex items-center gap-1 ${
                        isSelected
                          ? 'bg-stone-800 text-[#e0fd53] border border-stone-700'
                          : 'bg-[#edece4] text-[#16181a] border border-stone-300/80'
                      }`}
                    >
                      <TrendingUp className="w-3 h-3" />
                      <span>{imp.category}: +{imp.projected_demand_change_pct}%</span>
                    </span>
                  ))}
                </div>

                {/* Actionable Recommendation */}
                <div
                  className={`p-2.5 rounded-xl text-[11px] leading-relaxed flex items-start gap-2 ${
                    isSelected
                      ? 'bg-stone-800/90 text-stone-200 border border-stone-700'
                      : 'bg-[#f7f8f4] text-stone-700 border border-stone-200/80'
                  }`}
                >
                  <Sparkles
                    className={`w-3.5 h-3.5 shrink-0 mt-0.5 ${
                      isSelected ? 'text-[#e0fd53]' : 'text-[#16181a]'
                    }`}
                  />
                  <div>
                    <span className="font-bold">Inventory Prep: </span>
                    <span>{ev.recommended_action}</span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
