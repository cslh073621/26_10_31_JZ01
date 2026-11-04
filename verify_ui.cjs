// Execute selected scalar C function bodies as JavaScript with C integer division.
// Native compilation remains authoritative for PICC syntax/resource use; this is logic replay.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, 'PROJECT/main.c'), 'ascii').replace(/\r\n/g, '\n');
const clean = source.replace(/\/\*[\s\S]*?\*\//g, '');
const signatures = ['void KEY_CHECK(void)', 'void Key_Clear(void)', 'void KEY_deal(void)',
    'void mode_change_show(void)', 'void mode_change(void)', 'void show_mode_deal(void)', 'void smg_close(void)',
    'void smg_188_scan(void)', 'void pwm_init(void)', 'void file_sleep_mode(void)', 'u8 Get_Fin_Val(u16 temp_val)', 'void AD_fan_deal(void)'];
const macros = new Map([...clean.matchAll(/^#define\s+(\w+)\s+(.+)$/gm)].map(m => [m[1], m[2].trim()]));
let constants = '';
for (const [name, value] of macros) {
    if (/^(?:0x[0-9a-f]+|\d+)(?:UL)?$/i.test(value)) constants += `var ${name} = ${value.replace(/UL$/i, '')};\n`;
}
const globalNames = [...clean.matchAll(/^(?:bit|u8|u16)\s+(\w+)(?:\[(\d+)\])?;/gm)];
let globals = globalNames.map(m => `var ${m[1]} = ${m[2] ? 'Array(' + m[2] + ').fill(0)' : '0'};`).join('\n');
const table = clean.match(/const u8 app_smg\[11\] = \{([\s\S]*?)\};/)[1];
globals += `\nvar app_smg = [${table}];\n`;
const statics = new Set();
let code = '';
for (const signature of signatures) {
    const start = clean.indexOf(signature + '\n{');
    assert(start >= 0, signature);
    const first = clean.indexOf('{', start);
    let depth = 0, end;
    for (end = first; end < clean.length; end++) {
        if (clean[end] === '{') depth++;
        if (clean[end] === '}' && --depth === 0) break;
    }
    let body = clean.slice(first, end + 1);
    body = body.replace(/static u8 (\w+);/g, (_, name) => { statics.add(name); return ''; });
    body = body.replace(/\b(?:u8|u16)\s+/g, 'var ');
    body = body.replace(/\((?:u8|u16)\)/g, '');
    body = body.replace(/app_smg\[temp_val \/ 10\]/g, 'app_smg[Math.floor(temp_val / 10)]');
    for (const [name, value] of macros) {
        if (name.startsWith('IO_')) body = body.replace(new RegExp('\\b' + name + '\\b', 'g'), value);
    }
    const match = signature.match(/\w+ (\w+)\((.*)\)/);
    const params = match[2] === 'void' ? '' : match[2].replace(/\b(?:u8|u16)\s+/g, '');
    code += `function ${match[1]}(${params}) ${body}\n`;
}
globals += [...statics].map(name => `\nvar ${name} = 0;`).join('');
function fresh() {
    const ctx = {Math};
    const registers = {PORTA: 0, PORTC: 0, TRISA: 0x7F, TRISC: 0x07, T4C0:0, T4C1:0, T4PH:0, T4PL:0, T4DH:0, T4DL:0};
    ctx.trace = [];
    for (const [reg, initial] of Object.entries(registers)) {
        Object.defineProperty(ctx, reg, {get() {return registers[reg];}, set(value) {
            registers[reg] = value & 255;
            ctx.trace.push({...registers});
        }});
    }
    for (const port of ['A', 'C']) for (let bit = 0; bit < 8; bit++) {
        Object.defineProperty(ctx, 'P' + port + bit, {
            get() {return (registers['PORT' + port] >> bit) & 1;},
            set(value) {ctx['PORT' + port] = value ? registers['PORT' + port] | (1 << bit) : registers['PORT' + port] & ~(1 << bit);}
        });
    }
    for (const name of ['GIE','T3PWM3EN','T3REN','T3D3L','T3D3H']) ctx[name] = 0;
    vm.createContext(ctx);
    vm.runInContext(constants + globals + code, ctx);
    // GPIO aliases used in production C must remain register-backed.
    for (const [name, reg] of [['COOL_EN','PC5'],['FAN_ON','PC4'],['MOTOR_PWM','PC3'],['CHRG','PA5'],['STDBY','PA4']]) {
        Object.defineProperty(ctx, name, {get() {return ctx[reg];}, set(v) {ctx[reg] = v;}});
    }
    Object.defineProperty(ctx, 'T4REN', {get() {return ctx.T4C0 >> 7 & 1;}});
    Object.defineProperty(ctx, 'T4PWMEN', {get() {return ctx.T4C0 >> 1 & 1;}});
    ctx.Init_System = () => {};
    ctx.asm = instruction => {if (instruction === 'sleep') {assert.equal(ctx.T4C0,0); assert.equal(ctx.MOTOR_PWM,0);}};
    ctx.pwm_init();
    ctx.charge_num = 80; ctx.YOUWU_COOL = 1;
    ctx.KEY1 = ctx.KEY2 = ctx.KEY3 = 1;
    ctx.CHRG = ctx.STDBY = 1;
    return ctx;
}
function tick(c, count, key = 0) {
    for (let i = 0; i < count; i++) {
        c.KEY1 = key === 1 ? 0 : 1;
        c.KEY2 = key === 2 ? 0 : 1;
        c.KEY3 = key === 3 ? 0 : 1;
        c.KEY_CHECK(); c.KEY_deal(); c.mode_change();
    }
}
function click(c, key) {tick(c, 4, key); tick(c, 2);}
let c = fresh();
tick(c, 2, 2); tick(c, 2); assert.equal(c.fan_mode, 0, 'bounce cannot start');
tick(c, 300, 2); assert.equal(c.fan_mode, 1, 'held power starts once');
tick(c, 300, 2); assert.equal(c.fan_mode, 1, 'holding must not toggle repeatedly');
tick(c, 4); assert.equal(c.key2_click_cnt, 0, 'long release is not a click');
click(c, 2); tick(c, 40); assert.equal(c.fan_mode, 1); assert.equal(c.COOL_EN, 0);
assert.equal(c.key2_click_cnt, 0); assert.equal(c.key2_click_time, 0);
click(c, 2); tick(c, 10); click(c, 2); assert.equal(c.COOL_EN, 1, 'double click cooling on');
tick(c, 40); click(c, 2); click(c, 2); assert.equal(c.COOL_EN, 0, 'second double click cooling off');
click(c, 3); assert.equal(c.fan_mode, 2, '6.8k up one');
click(c, 1); assert.equal(c.fan_mode, 1, '20k down one');
tick(c, 100, 3); assert(c.fan_mode > 3 && c.fan_mode < 100, 'long up repeats');
tick(c, 2000, 3); assert.equal(c.fan_mode, 100, 'upper bound saturates');
tick(c, 4); click(c, 3); assert.equal(c.fan_mode, 100);
tick(c, 2000, 1); assert.equal(c.fan_mode, 1, 'lower bound saturates');
tick(c, 4); click(c, 1); assert.equal(c.fan_mode, 1);
c.COOL_EN = 1; tick(c, 300, 2); assert.equal(c.fan_mode, 0); assert.equal(c.COOL_EN, 0);
tick(c, 4); click(c, 3); tick(c, 200, 1); assert.equal(c.fan_mode, 0, 'up/down never start from off');
c = fresh(); c.fan_mode = 1; c.CHRG = 0; c.mode_change();
click(c, 2); click(c, 2); assert.equal(c.COOL_EN, 0, 'retain baseline charging cooling interlock');
let patterns = 0;
function lampMask(count){return count ? (31 << (5-count)) & 31 : 0;}
function advanceFlow(c){c.time_500ms_flag=1;c.mode_change_show();c.show_mode_deal();}
for (let q=0;q<=100;q++) for(const on of [0,1]) for(const inserted of [0,1]) for(const full of [0,1]) {
    c=fresh();Object.assign(c,{charge_num:q,fan_mode:on,insert_flag:inserted,charge_max_flag:full});
    c.show_mode_deal();
    if(inserted && q<100){
        const lower=q===0?0:Math.floor((q-1)/20);
        const remaining=5-lower;
        for(let phase=0;phase<=remaining;phase++){
            assert.equal(c.Data[3],lampMask(lower+phase),`flow q=${q} phase=${phase} full=${full}`);
            if(!on) assert.deepEqual(Array.from(c.Data.slice(0,3)),[0,0,0]);
            patterns++;advanceFlow(c);
        }
        assert.equal(c.Data[3],lampMask(lower),'full returns to steady lower intervals');
    } else {
        const lowBlink=!inserted && on && q>0 && q<=20;
        const expected=(on || inserted) && q>0 ? lampMask(Math.ceil(q/20)) : 0;
        for(let frame=0;frame<7;frame++){
            assert.equal(c.Data[3],lowBlink ? (frame%2 ? 16 : 0) : expected,'low battery blink / other bars steady');
            if(!on) assert.deepEqual(Array.from(c.Data.slice(0,3)),[0,0,0]);
            patterns++;advanceFlow(c);
        }
    }
}
// Low-battery transitions: charging flow, unplugging, threshold and stopping.
c=fresh();Object.assign(c,{charge_num:20,fan_mode:100});c.show_mode_deal();
for(const mask of [0,16,0,16]){assert.equal(c.Data[3],mask);advanceFlow(c);}
c.charge_num=21;c.show_mode_deal();assert.equal(c.Data[3],24);
c.charge_num=1;c.show_mode_deal();advanceFlow(c);assert.equal(c.Data[3],16);
c.insert_flag=1;c.show_mode_deal();
for(const mask of [16,24,28,30,31,0]){assert.equal(c.Data[3],mask);advanceFlow(c);}
c.insert_flag=0;c.show_mode_deal();assert.equal(c.Data[3]&15,0);
c.fan_mode=0;c.show_mode_deal();assert.equal(c.Data[3],0);assert.equal(c.charge_led_flow,0);
c.low_cnt=3;c.show_mode_deal();assert.equal(c.Data[3],16,'off-state low indication retained');
c.low_cnt=0;c.charge_num=0;c.fan_mode=1;c.show_mode_deal();assert.equal(c.Data[3],0);
// User examples, range transitions, disconnect/reconnect and 100% without STDBY.
c=fresh();c.insert_flag=1;c.charge_num=5;c.show_mode_deal();
for(const mask of [0,16,24,28,30,31,0]){assert.equal(c.Data[3],mask);advanceFlow(c);}
c.charge_num=21;c.show_mode_deal();assert.equal(c.Data[3],16);
for(const mask of [16,24,28,30,31,16]){assert.equal(c.Data[3],mask);advanceFlow(c);}
c.charge_num=41;c.show_mode_deal();assert.equal(c.Data[3],24);
c.insert_flag=0;c.show_mode_deal();assert.equal(c.Data[3],0);assert.equal(c.charge_led_flow,0);
c.insert_flag=1;c.charge_num=21;c.show_mode_deal();assert.equal(c.Data[3],16);
c.charge_num=100;c.charge_max_flag=0;c.show_mode_deal();
for(let i=0;i<8;i++){assert.equal(c.Data[3],31);advanceFlow(c);}
const digits = [0x3F,0x06,0x5B,0x4F,0x66,0x6D,0x7D,0x07,0x7F,0x6F];
for (let gear = 1; gear <= 100; gear++) for (const cool of [0,1]) {
    c = fresh(); c.fan_mode = gear; c.COOL_EN = cool; c.show_mode_deal();
    assert.equal(c.Data[0], 4 | (gear === 100 ? 3 : 0) | (cool ? 8 : 0));
    assert.equal(c.Data[1], (gear < 10 ? 0 : digits[Math.floor(gear % 100 / 10)]));
    assert.equal(c.Data[2], digits[gear % 10]);
    c.insert_flag = 1; c.show_mode_deal();
    assert.equal(c.Data[1], (gear < 10 ? 0 : digits[Math.floor(gear % 100 / 10)]), 'charging still displays gear');
    assert.equal(c.Data[2], digits[gear % 10]);
}
const pinBits = [['A',0],['A',1],['A',2],['A',3],['C',0],['C',2]];
function levels(state) {return pinBits.map(([port, bit]) => state['TRIS'+port] & (1<<bit) ? -1 : (state['PORT'+port] >> bit) & 1);}
c = fresh(); c.PORTC = 0x38; c.Data = [15,127,127,0x15];
for (let iteration = 0; iteration < 12; iteration++) {
    const slot = iteration % 6 + 1;
    c.trace.length = 0; c.smg_188_scan();
    const last = c.trace.at(-1); const pins = levels(last);
    if (slot < 6) {
        assert.equal(pins[5], -1, 'S6 isolated during 188 slots');
        assert.equal(pins[slot-1], 0, 'FanForge standard low row');
        assert.equal(pins.filter(x=>x===0).length, 1);
    } else {
        assert.deepEqual(pins, [1,-1,1,-1,1,0], 'common-cathode slot sources only lit LEDs');
    }
    for (const state of c.trace) {
        assert.equal(state.PORTC & 0x38, 0x38, 'scan cannot alter boost/cooling/motor control pins');
        const pins = levels(state);
        if (pins[5] === 0) assert(pins.slice(0,5).every(x=>x!==0), 'never overlap a low 188 row with active S6');
    }
}
// Every five-lamp mask must use the same active-high/default-output convention.
for (let mask=0;mask<32;mask++) {
    c=fresh();c.PORTC=0x38;c.Data=[0,0,0,mask];
    for(let slot=1;slot<=6;slot++) c.smg_188_scan();
    const pins=levels(c.trace.at(-1));
    assert.deepEqual(pins.slice(0,5),Array.from({length:5},(_,i)=>mask&(1<<i)?1:-1));
    assert.equal(pins[5],0);
    c.trace.length=0;c.smg_188_scan();
    for(const state of c.trace){
        assert.equal(state.PORTC&0x38,0x38);
        const v=levels(state);
        if(v[5]===0) assert(v.slice(0,5).every(x=>x!==0),'S6 must be blanked before the next 188 low row');
    }
}
// Mature 10ms-call start/stop path and valid-mean overvoltage shutdown.
c = fresh(); c.fan_mode = 1; c.AD_fan_deal(); assert.equal(c.FAN_ON,1); assert.equal(c.T3PWM3EN,0);
c.AD_fan_deal(); assert.equal(c.T3PWM3EN,1);
c.fan_mode=0; c.AD_fan_deal(); assert.equal(c.T3PWM3EN,0); assert.equal(c.FAN_ON,1);
c.AD_fan_deal(); assert.equal(c.FAN_ON,0);
c.fan_mode=1; c.AD_fan_deal(); c.AD_fan_deal();
for (let i=0;i<13;i++) {c.AD_FAN_VALUE=2979;c.ad_fan_ready_flag=1;c.AD_fan_deal();}
assert.equal(c.fan_error_flag,1);assert.equal(c.fan_mode,0);assert.equal(c.T3PWM3EN,0);
// Restored template limit: >10V and 15V samples are not overvoltage faults.
for(const raw of [1862,2792,2978]) {
    c=fresh();c.fan_mode=1;c.FAN_ON=1;c.T3PWM3EN=1;c.T3REN=1;
    for(let i=0;i<20;i++){c.AD_FAN_VALUE=raw;c.ad_fan_ready_flag=1;c.AD_fan_deal();}
    assert.equal(c.fan_error_flag,0,'no protection trip below/equal template limit');
    assert.equal(c.too_big_cnt,0);
}
// Independent motor PWM: 640 nominal ticks, all gears, stopped/fault/sleep.
c = fresh(); assert.equal(c.T4C0,0); assert.equal(c.T4C1,0x17);
assert.equal((c.T4PH << 8) | c.T4PL,639); assert.equal(c.PWMSEL1 & 12,0);
let previous = -1;
for (let gear=1; gear<=100; gear++) {
    c = fresh(); c.fan_mode=gear; c.FAN_ON=1; c.T3PWM3EN=1; c.T3REN=1;
    c.AD_fan_deal();
    const duty=(c.T4DH<<8)|c.T4DL;
    const expected=224+Math.floor((400*(gear-1)+49)/99);
    assert.equal(duty,expected,'linear motor command gear '+gear);
    assert(duty>previous); previous=duty;
    assert.equal(c.T4C0,0x82);assert.equal(c.T3PL,63);assert.equal(c.T3C1,0x17);
    c.fan_mode=0;c.AD_fan_deal();assert.equal(c.T4C0,0);assert.equal(c.MOTOR_PWM,0);
}
c=fresh();c.fan_mode=1;c.AD_fan_deal();assert.equal(c.T4C0,0);
c.AD_fan_deal();assert.equal(c.T4C0,0);c.AD_fan_deal();assert.equal(c.T4C0,0x82);
c.AD_FAN_VALUE=2979;
for(let i=0;i<13;i++){c.ad_fan_ready_flag=1;c.AD_fan_deal();}
assert.equal(c.T4C0,0);assert.equal(c.MOTOR_PWM,0);
c=fresh();c.T4C0=0x82;c.MOTOR_PWM=1;c.file_sleep_mode();assert.equal(c.T4C0,0);assert.equal(c.MOTOR_PWM,0);
// Use the actual main-loop sleep predicate: only the physical power key matters.
const sleepExpression=source.match(/if\((!low_cnt && !fan_mode && !insert_flag[\s\S]*?)\)\s*\{\s*file_sleep_mode\(\);/)[1];
function maySleep(context){return !!vm.runInContext('('+sleepExpression+')',context);}
c=fresh();c.KEY1=0;c.KEY3=0;c.key1_down_flag=1;c.key3_down_flag=1;
c.key1_short_flag=c.key2_short_flag=c.key3_short_flag=1;
c.key1_long_flag=c.key2_long_flag=c.key3_long_flag=1;
c.key2_click_cnt=1;c.key2_click_time=10;
assert.equal(maySleep(c),true,'off-state +/- events and click bookkeeping do not block sleep');
c.KEY2=0;assert.equal(maySleep(c),false,'held power key blocks sleep');c.KEY2=1;
for(const name of ['fan_mode','insert_flag','low_cnt','wake_guard_cnt','T3PWM3EN','T3REN']){
 c[name]=1;assert.equal(maySleep(c),false,name+' retains its sleep gate');c[name]=0;
}
c.FAN_ON=1;assert.equal(maySleep(c),false);c.FAN_ON=0;
c.T4C0=0x82;assert.equal(maySleep(c),false);c.T4C0=0;
assert.equal(maySleep(c),true);
console.log('PASS: simplified actual sleep predicate; power held blocks; +/- events/click bookkeeping ignored; operating/charging/output gates retained.');
console.log('PASS: motor T4 25kHz nominal period, all 100 linear duties, enable sequence, stop/fault/sleep command removal.');
console.log(`PASS: actual C-body logic replay; power long/double/bounce; +/- repeat and bounds; ${patterns} battery flow/static frames; 200 gear/icon states; six-slot GPIO isolation; mature start/stop and protection.`);
console.log('Assumptions: 10ms driver calls and C integer division; does not model ADC acquisition, PICC execution time, LED current, or real board light behavior.');
