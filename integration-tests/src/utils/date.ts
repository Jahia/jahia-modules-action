import {
  format,
  differenceInHours,
  differenceInMinutes,
  differenceInSeconds
} from 'date-fns'

export const timeSinceStart = (stardDate: Date) => {
  const currentDate = new Date()
  return `[+${Math.round(
    differenceInHours(currentDate, stardDate)
  )}:${Math.round(differenceInMinutes(currentDate, stardDate))}:${Math.round(
    differenceInSeconds(currentDate, stardDate)
  )}]`
}

export const formatDate = (date: Date) => {
  return format(date, 'PPPP pppp')
}
