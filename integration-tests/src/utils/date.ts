import {format, differenceInSeconds} from 'date-fns'

// Return time since start in the [+HH:MM:SS] format
export const timeSinceStart = (stardDate: Date) => {
  const currentDate = new Date()
  let secondsDiff = differenceInSeconds(currentDate, stardDate)

  let hours: number = 0
  let minutes: number = 0
  let seconds: number = 0

  if (secondsDiff > 3600) {
    hours = Math.round(secondsDiff / 3600)
    secondsDiff = secondsDiff - hours * 3600
  }

  if (secondsDiff > 60) {
    minutes = Math.round(secondsDiff / 60)
    secondsDiff = secondsDiff - minutes * 3600
  }

  if (secondsDiff > 0) {
    seconds = secondsDiff
  }

  return `[+${hours < 10 ? `0${hours}` : hours}:${
    minutes < 10 ? `0${minutes}` : minutes
  }:${seconds < 10 ? `0${seconds}` : seconds}]`
}

export const formatDate = (date: Date) => {
  return format(date, 'PPPP pppp')
}
