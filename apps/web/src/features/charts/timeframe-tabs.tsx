"use client";

import {
  Tabs,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { TIMEFRAMES, type TimeframeKey } from "@/features/charts/types";

function isTimeframeKey(value: string): value is TimeframeKey {
  return TIMEFRAMES.some((item) => item.key === value);
}

export function TimeframeTabs({
  value,
  onChange,
}: {
  value: TimeframeKey;
  onChange: (value: TimeframeKey) => void;
}) {
  return (
    <Tabs
      value={value}
      onValueChange={(nextValue) => {
        if (isTimeframeKey(nextValue)) {
          onChange(nextValue);
        }
      }}
      className="w-full md:w-auto"
    >
      <TabsList className="grid w-full grid-cols-5 md:w-fit">
        {TIMEFRAMES.map((timeframe) => (
          <TabsTrigger key={timeframe.key} value={timeframe.key}>
            {timeframe.label}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  );
}
