// Big Clear: Amazfit round face (466 and 480). Declarative widgets only:
// the OS draws time, date and data. There are no timers and no sensor
// subscriptions, so nothing in this file runs after build(). The one
// exception is the step count above 10K, which needs a step-change callback.
import ui from '@zos/ui'
import { Step } from '@zos/sensor'
import { layout as L } from 'zosLoader:./[name].[pf].layout.js'

const SL = ui.show_level
const NORMAL = SL.ONLY_NORMAL
const AOD = SL.ONAL_AOD
const A = ui.align
const DT = ui.data_type
const ET = ui.edit_type
const W = ui.widget

// Custom Edit-mode choices.
const OFF = 100001
const SOLID = 100002
const OUTLINE = 100003
const WX_FULL = 100004
const WX_TEMP = 100005
const DATE_ON = 100006

const img = (name) => 'images/' + name + '.png'
const seq = (prefix, n) => {
  const list = []
  for (let i = 0; i < n; i++) list.push(img(prefix + i))
  return list
}
const all3 = (key, value) => {
  const o = {}
  o[key + '_en'] = value
  o[key + '_sc'] = value
  o[key + '_tc'] = value
  return o
}

function editGroup(name, defType, options) {
  const g = L.groups[name]
  const group = ui.createWidget(W.WATCHFACE_EDIT_GROUP, {
    edit_id: g.id,
    x: g.x,
    y: g.y,
    w: g.w,
    h: g.h,
    select_image: img('edit/sel_' + name),
    un_select_image: img('edit/un_' + name),
    default_type: defType,
    optional_types: options.map((o) => {
      const t = { type: o.type, preview: img('edit/pv_' + name + '_' + o.key) }
      if (o.en) {
        t.title_en = o.en
        t.title_sc = o.sc
        t.title_tc = o.tc
      }
      return t
    }),
    count: options.length,
    tips_BG: img('edit/tips'),
    tips_x: g.tx,
    tips_y: g.ty,
    tips_width: L.tipW,
  })
  return group.getProperty(ui.prop.CURRENT_TYPE)
}

const OFF_OPTION = { type: OFF, key: 'off', en: 'Off', sc: '关闭', tc: '關閉' }

function dndMask(name, x, y) {
  ui.createWidget(W.IMG_STATUS, {
    x,
    y,
    type: ui.system_status.DISTURB,
    src: img('mask/' + name),
    show_level: NORMAL,
  })
}

function textImg(props) {
  return ui.createWidget(W.TEXT_IMG, Object.assign({ h_space: 0, show_level: NORMAL }, props))
}

function valueText(c, type, extra) {
  return textImg(
    Object.assign(
      { x: c.vx, y: c.vy, w: c.vw, h: c.vh, font_array: seq('val/', 10), align_h: A.CENTER_H, type },
      extra
    )
  )
}

function drawTime(style) {
  const t = L.time
  const solid = style === SOLID
  const prefix = 'time/' + (solid ? 's' : 'o')
  ui.createWidget(W.IMG_TIME, {
    hour_startX: t.hx,
    hour_startY: t.hy,
    hour_array: seq(prefix, 10),
    hour_zero: 1,
    hour_space: 0,
    hour_align: A.LEFT,
    minute_startX: t.mx,
    minute_startY: t.my,
    minute_array: seq(prefix, 10),
    minute_zero: 1,
    minute_space: 0,
    minute_align: A.LEFT,
    minute_follow: 0,
    am_x: t.ax,
    am_y: t.ay,
    am_en_path: img('time/am'),
    am_sc_path: img('time/am'),
    am_tc_path: img('time/am'),
    pm_x: t.ax,
    pm_y: t.ay,
    pm_en_path: img('time/pm'),
    pm_sc_path: img('time/pm'),
    pm_tc_path: img('time/pm'),
    show_level: NORMAL,
  })
}

function drawDate(aod) {
  const d = L.date
  const p = aod ? 'date/a' : 'date/'
  const level = aod ? AOD : NORMAL
  const weeks = seq(p + 'wk', 7)
  const months = seq(p + 'mo', 12)
  const days = []
  for (let i = 1; i <= 31; i++) days.push(img(p + 'day' + i))
  ui.createWidget(W.IMG_WEEK, {
    x: d.wx,
    y: d.y,
    week_en: weeks,
    week_sc: weeks,
    week_tc: weeks,
    show_level: level,
  })
  ui.createWidget(W.IMG_DATE, {
    month_startX: d.mx,
    month_startY: d.y,
    month_is_character: true,
    month_en_array: months,
    month_sc_array: months,
    month_tc_array: months,
    month_align: A.LEFT,
    month_follow: 0,
    day_startX: d.dx,
    day_startY: d.y,
    day_is_character: true,
    day_follow: 0,
    day_zero: 0,
    day_space: 0,
    day_align: A.LEFT,
    day_en_array: days,
    day_sc_array: days,
    day_tc_array: days,
    show_level: level,
  })
}

function drawWeather(full) {
  const w = L.wx
  const icons = L.weatherIcons.map((n) => img('wx/i_' + n))
  ui.createWidget(W.IMG_LEVEL, {
    x: w.ix,
    y: w.iy,
    image_array: icons,
    image_length: icons.length,
    type: DT.WEATHER,
    show_level: NORMAL,
  })
  const deg = img('wx/deg')
  textImg({
    x: w.tx,
    y: w.ty,
    w: w.tw,
    h: w.th,
    font_array: seq('wx/t', 10),
    align_h: A.LEFT,
    type: DT.WEATHER_CURRENT,
    unit_en: deg,
    unit_sc: deg,
    unit_tc: deg,
    imperial_unit_en: deg,
    imperial_unit_sc: deg,
    imperial_unit_tc: deg,
    negative_image: img('wx/neg'),
    invalid_image: img('wx/inv'),
  })
  if (!full) return
  ui.createWidget(W.IMG, { x: w.uix, y: w.uiy, src: img('wx/up'), show_level: NORMAL })
  ui.createWidget(W.IMG, { x: w.dix, y: w.diy, src: img('wx/down'), show_level: NORMAL })
  const small = {
    font_array: seq('wx/h', 10),
    align_h: A.LEFT,
    negative_image: img('wx/hneg'),
    invalid_image: img('wx/hinv'),
  }
  textImg(Object.assign({ x: w.ux, y: w.uy, w: w.uw, h: w.uh, type: DT.WEATHER_HIGH }, small))
  textImg(Object.assign({ x: w.dx, y: w.dy, w: w.dw, h: w.dh, type: DT.WEATHER_LOW }, small))
}

function drawCalorie() {
  const c = L.corner.cal
  ui.createWidget(W.IMG, { x: c.ix, y: c.iy, src: img('icon/flame'), show_level: NORMAL })
  valueText(c, DT.CAL)
}

function drawHeart() {
  const c = L.corner.hr
  ui.createWidget(W.IMG, { x: c.ix, y: c.iy, src: img('icon/heart'), show_level: NORMAL })
  valueText(c, DT.HEART, { invalid_image: img('val/inv') })
}

// 10473 -> ['1','0','dot','4','k']. Floored, so it never reads higher than the real count.
function stepGlyphs(n) {
  const tenths = Math.floor(n / 100)
  const text = tenths >= 1000 ? Math.floor(tenths / 10) + 'K' : Math.floor(tenths / 10) + '.' + (tenths % 10) + 'K'
  return text.split('').map((ch) => (ch === '.' ? 'dot' : ch === 'K' ? 'k' : ch))
}

// Below 10K the OS draws the count by itself. From 10K up, the native text hides
// and a few IMG widgets show "10.4K", updated only when the step count changes.
function drawStepsK(native) {
  const K = L.stepsK
  const slots = []
  for (let i = 0; i < 5; i++) {
    const w = ui.createWidget(W.IMG, { x: 0, y: K.y, src: img('val/k'), show_level: NORMAL })
    w.setProperty(ui.prop.VISIBLE, false)
    slots.push(w)
  }
  const width = (g) => (g === 'dot' ? K.dot : g === 'k' ? K.k : K.cell)
  const step = new Step()
  let shown = -1
  const update = () => {
    const n = step.getCurrent()
    console.log('steps ' + n)
    const big = n >= K.from
    const key = big ? Math.floor(n / 100) : 0
    if (key === shown) return
    shown = key
    native.setProperty(ui.prop.VISIBLE, !big)
    const glyphs = big ? stepGlyphs(n) : []
    let x = Math.round(K.cx - glyphs.reduce((sum, g) => sum + width(g), 0) / 2)
    slots.forEach((w, i) => {
      const g = glyphs[i]
      if (g) {
        w.setProperty(ui.prop.MORE, { x, y: K.y, w: width(g), h: K.h, src: img('val/' + g) })
        x += width(g)
      }
      w.setProperty(ui.prop.VISIBLE, !!g)
    })
  }
  update()
  step.onChange(update)
  ui.createWidget(W.WIDGET_DELEGATE, { resume_call: update })
  return () => step.offChange(update)
}

let stopSteps = null

function drawSteps() {
  const c = L.corner.steps
  ui.createWidget(W.IMG, { x: c.ix, y: c.iy, src: img('icon/steps'), show_level: NORMAL })
  const native = valueText(c, DT.STEP)
  stopSteps = drawStepsK(native)
  ui.createWidget(W.IMG_LEVEL, {
    x: c.bx,
    y: c.by,
    image_array: seq('bar/', L.stepBarLevels),
    image_length: L.stepBarLevels,
    type: DT.STEP,
    show_level: NORMAL,
  })
}

function drawBattery() {
  const c = L.corner.bat
  const pct = img('val/pct')
  const icons = L.batteryIcons.map(img)
  ui.createWidget(W.IMG_LEVEL, {
    x: c.ix,
    y: c.iy,
    image_array: icons,
    image_length: icons.length,
    type: DT.BATTERY,
    show_level: NORMAL,
  })
  valueText(c, DT.BATTERY, { unit_en: pct, unit_sc: pct, unit_tc: pct })
}

function drawBatteryAod() {
  const c = L.corner.bat
  const pct = img('val/apct')
  const icons = L.batteryIconsAod.map(img)
  ui.createWidget(W.IMG_LEVEL, {
    x: c.ix,
    y: c.iy,
    image_array: icons,
    image_length: icons.length,
    type: DT.BATTERY,
    show_level: AOD,
  })
  ui.createWidget(W.TEXT_IMG, {
    x: c.vx,
    y: c.vy,
    w: c.vw,
    h: c.vh,
    font_array: seq('val/a', 10),
    h_space: 0,
    align_h: A.CENTER_H,
    type: DT.BATTERY,
    unit_en: pct,
    unit_sc: pct,
    unit_tc: pct,
    show_level: AOD,
  })
}

function drawTimeAod() {
  const t = L.time
  const digits = seq('time/a', 10)
  ui.createWidget(W.IMG_TIME, {
    hour_startX: t.hx,
    hour_startY: t.hy,
    hour_array: digits,
    hour_zero: 1,
    hour_space: 0,
    hour_align: A.LEFT,
    minute_startX: t.mx,
    minute_startY: t.my,
    minute_array: digits,
    minute_zero: 1,
    minute_space: 0,
    minute_align: A.LEFT,
    minute_follow: 0,
    am_x: t.ax,
    am_y: t.ay,
    am_en_path: img('time/am'),
    am_sc_path: img('time/am'),
    am_tc_path: img('time/am'),
    pm_x: t.ax,
    pm_y: t.ay,
    pm_en_path: img('time/pm'),
    pm_sc_path: img('time/pm'),
    pm_tc_path: img('time/pm'),
    show_level: AOD,
  })
}

WatchFace({
  build() {
    const style = editGroup('time', SOLID, [
      { type: SOLID, key: 'solid', en: 'Solid time', sc: '实心时间', tc: '實心時間' },
      { type: OUTLINE, key: 'outline', en: 'Outline time', sc: '空心时间', tc: '空心時間' },
    ])
    const weather = editGroup('wx', WX_FULL, [
      { type: WX_FULL, key: 'full', en: 'Weather, high and low', sc: '天气和高低温', tc: '天氣和高低溫' },
      { type: WX_TEMP, key: 'temp', en: 'Weather only', sc: '仅天气', tc: '僅天氣' },
      OFF_OPTION,
    ])
    const date = editGroup('date', DATE_ON, [
      { type: DATE_ON, key: 'on', en: 'Date', sc: '日期', tc: '日期' },
      OFF_OPTION,
    ])
    const cal = editGroup('cal', ET.CAL, [{ type: ET.CAL, key: 'on' }, OFF_OPTION])
    const bat = editGroup('bat', ET.BATTERY, [{ type: ET.BATTERY, key: 'on' }, OFF_OPTION])
    const hr = editGroup('hr', ET.HEART, [{ type: ET.HEART, key: 'on' }, OFF_OPTION])
    const steps = editGroup('steps', ET.STEP, [{ type: ET.STEP, key: 'on' }, OFF_OPTION])

    // Always-on display: dim outline time, date and battery only.
    drawTimeAod()
    if (date !== OFF) drawDate(true)
    if (bat !== OFF) drawBatteryAod()

    // Active display.
    drawTime(style)
    if (date !== OFF) drawDate(false)
    if (weather !== OFF) drawWeather(weather === WX_FULL)
    if (cal !== OFF) drawCalorie()
    if (bat !== OFF) drawBattery()
    if (hr !== OFF) drawHeart()
    if (steps !== OFF) drawSteps()

    // Do Not Disturb (Zepp turns it on in sleep mode): black out the data, dim the time.
    const g = L.groups
    dndMask('time', g.time.x, g.time.y)
    dndMask('ampm', L.ampmMask.x, L.ampmMask.y)
    if (date !== OFF) dndMask('date', g.date.x, g.date.y)
    if (weather !== OFF) dndMask('wx', g.wx.x, g.wx.y)
    if (cal !== OFF) dndMask('cal', g.cal.x, g.cal.y)
    if (bat !== OFF) dndMask('bat', g.bat.x, g.bat.y)
    if (hr !== OFF) dndMask('hr', g.hr.x, g.hr.y)
    if (steps !== OFF) dndMask('steps', g.steps.x, g.steps.y)

    ui.createWidget(W.WATCHFACE_EDIT_MASK, {
      x: 0,
      y: 0,
      w: L.W,
      h: L.W,
      src: img('edit/mask100'),
      show_level: SL.ONLY_EDIT,
    })
    ui.createWidget(W.WATCHFACE_EDIT_FG_MASK, {
      x: 0,
      y: 0,
      w: L.W,
      h: L.W,
      src: img('edit/mask70'),
      show_level: SL.ONLY_EDIT,
    })
  },

  onDestroy() {
    if (stopSteps) stopSteps()
    stopSteps = null
  },
})
