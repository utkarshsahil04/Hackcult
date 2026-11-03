export const springs={soft:{stiffness:170,damping:22},snappy:{stiffness:380,damping:28}} as const
export const durations={fast:0.18,base:0.35,slow:0.7,intro:2.8} as const
export const delays={matchLabel:0.25,matchTitle:0.45,candidate:0.1,wordmark:0.85,subtitle:1.6} as const
export const ease=[0.22,1,0.36,1] as const
export const stagger=(index:number)=>index*0.06
export const transitions={fast:{duration:durations.fast,ease},base:{duration:durations.base,ease},slow:{duration:durations.slow,ease}} as const
export const reducedMotion={initial:{opacity:0},animate:{opacity:1,transition:{duration:durations.fast,ease}},exit:{opacity:0,transition:{duration:durations.fast,ease}}} as const
export const fade={initial:{opacity:0},animate:{opacity:1,transition:transitions.base},exit:{opacity:0,transition:transitions.fast}}
