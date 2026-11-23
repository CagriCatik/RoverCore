/* Board I/O for ESP-IDF v5.x, see board_io.h. */
#include "board_io.h"

#include "driver/gpio.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_attr.h"
#include "esp_system.h"
#include "esp_timer.h"

#include "rovercore_pins.h"
#include "sense.h"

/* ADC1 channels of the analog pins (ESP32-S3: GPIO1..10 = ADC1_CH0..9; pinmap: CH0, CH3, CH4) */
#define ADC_CH_ISERVO ADC_CHANNEL_0  /* GPIO1 */
#define ADC_CH_VBAT ADC_CHANNEL_3    /* GPIO4 */
#define ADC_CH_VSERVO ADC_CHANNEL_4  /* GPIO5 */
_Static_assert(PIN_ISERVO_SENSE == 1 && PIN_VBAT_SENSE == 4 && PIN_VSERVO_SENSE == 5, "ADC channel map vs pinmap");

static adc_oneshot_unit_handle_t s_adc;
static adc_cali_handle_t s_cali;
static bool s_adc_ok, s_cali_ok;
static bio_config_t s_cfg;
static volatile uint32_t s_armed_fell;   /* set by the GPIO18 falling-edge interrupt */

static void IRAM_ATTR armed_isr(void *arg)
{
    (void)arg;
    s_armed_fell = 1;
}

static void out_level(int pin, int level)
{
    /* level first, then direction: no glitch to the opposite level */
    gpio_set_level(pin, level);
    gpio_config_t c = {.pin_bit_mask = 1ULL << pin, .mode = GPIO_MODE_OUTPUT, .pull_up_en = GPIO_PULLUP_DISABLE,
                       .pull_down_en = GPIO_PULLDOWN_DISABLE, .intr_type = GPIO_INTR_DISABLE};
    gpio_config(&c);
    gpio_set_level(pin, level);
}

static void in_plain(int pin, bool pull_up, bool pull_down, gpio_int_type_t intr)
{
    gpio_config_t c = {.pin_bit_mask = 1ULL << pin, .mode = GPIO_MODE_INPUT,
                       .pull_up_en = pull_up ? GPIO_PULLUP_ENABLE : GPIO_PULLUP_DISABLE,
                       .pull_down_en = pull_down ? GPIO_PULLDOWN_ENABLE : GPIO_PULLDOWN_DISABLE, .intr_type = intr};
    gpio_config(&c);
}

int bio_safe_init(const bio_config_t *cfg)
{
    s_cfg = *cfg;
    /* 1. locked outputs (also the state the hardware pulls give while these pins are Hi-Z) */
    out_level(PIN_SERVO_PWR_EN, 0);   /* servo rail off */
    out_level(PIN_ACT_OE_N, 1);       /* pulse buffers U201 disabled */
    out_level(PIN_STATUS_LED, 0);
    out_level(PIN_BUZZER, 0);
    /* 2. inputs without internal pulls (pinmap); bench option for a bare DevKit only */
    in_plain(PIN_ENABLE_BTN, cfg->bench_pulls, false, GPIO_INTR_DISABLE);
    in_plain(PIN_ACT_ARMED_FB, false, cfg->bench_pulls, GPIO_INTR_NEGEDGE);
    in_plain(PIN_IMU_INT1, false, false, GPIO_INTR_DISABLE);   /* never drive GPIO6 (IMU strap) */
    /* pulse lines GPIO13-17 and LED data GPIO39-42 stay in their reset Hi-Z state in this stage:
     * Hi-Z + U201 disabled + gate pull-ups -> lines low, no pulse (pinmap boot_state). Not touched here. */
    int err = gpio_install_isr_service(0);
    if (err == 0) err = gpio_isr_handler_add(PIN_ACT_ARMED_FB, armed_isr, NULL);
    /* 3. ADC1, 12 dB attenuation (0 ... about 3.1 V) */
    adc_oneshot_unit_init_cfg_t ucfg = {.unit_id = ADC_UNIT_1};
    if (adc_oneshot_new_unit(&ucfg, &s_adc) == ESP_OK) {
        adc_oneshot_chan_cfg_t ccfg = {.atten = ADC_ATTEN_DB_12, .bitwidth = ADC_BITWIDTH_DEFAULT};
        s_adc_ok = adc_oneshot_config_channel(s_adc, ADC_CH_VBAT, &ccfg) == ESP_OK &&
                   adc_oneshot_config_channel(s_adc, ADC_CH_VSERVO, &ccfg) == ESP_OK &&
                   adc_oneshot_config_channel(s_adc, ADC_CH_ISERVO, &ccfg) == ESP_OK;
        adc_cali_curve_fitting_config_t kcfg = {.unit_id = ADC_UNIT_1, .atten = ADC_ATTEN_DB_12,
                                                .bitwidth = ADC_BITWIDTH_DEFAULT};
        s_cali_ok = adc_cali_create_scheme_curve_fitting(&kcfg, &s_cali) == ESP_OK;
    }
    return err;
}

static bool read_mv(adc_channel_t ch, uint32_t *mv)
{
    int raw = 0, v = 0;
    if (!s_adc_ok || !s_cali_ok || adc_oneshot_read(s_adc, ch, &raw) != ESP_OK ||
        adc_cali_raw_to_voltage(s_cali, raw, &v) != ESP_OK || v < 0) {
        return false;
    }
    *mv = (uint32_t)v;
    return true;
}

void bio_read(sv_inputs_t *in)
{
    in->button_pressed = gpio_get_level(PIN_ENABLE_BTN) == 0;   /* active low */
    in->act_armed = gpio_get_level(PIN_ACT_ARMED_FB) == 1;
    in->act_armed_fell = s_armed_fell != 0;
    s_armed_fell = 0;
    uint32_t mv = 0;
    in->vbat_valid = read_mv(ADC_CH_VBAT, &mv);
    in->vbat_mv = in->vbat_valid ? sense_vbat_mv(mv) : 0;
    in->vservo_mv = read_mv(ADC_CH_VSERVO, &mv) ? sense_vservo_mv(mv) : 0;
    in->iservo_ma = read_mv(ADC_CH_ISERVO, &mv) ? sense_iservo_ma(mv) : -1;
    if (s_cfg.bench_supply) {
        in->vbat_valid = true;
        in->vbat_mv = 12000;
    }
}

void bio_apply(const sv_outputs_t *o)
{
    gpio_set_level(PIN_SERVO_PWR_EN, o->servo_pwr_en ? 1 : 0);
    gpio_set_level(PIN_ACT_OE_N, o->act_oe_n ? 1 : 0);
}

void bio_status_led(bool on) { gpio_set_level(PIN_STATUS_LED, on ? 1 : 0); }

uint32_t bio_now_ms(void) { return (uint32_t)(esp_timer_get_time() / 1000); }

const char *bio_reset_reason(void)
{
    switch (esp_reset_reason()) {
    case ESP_RST_POWERON: return "power-on";
    case ESP_RST_EXT: return "external pin (EN)";
    case ESP_RST_SW: return "software";
    case ESP_RST_PANIC: return "panic";
    case ESP_RST_INT_WDT: return "interrupt watchdog";
    case ESP_RST_TASK_WDT: return "task watchdog";
    case ESP_RST_WDT: return "other watchdog";
    case ESP_RST_DEEPSLEEP: return "deep sleep";
    case ESP_RST_BROWNOUT: return "brown-out";
    case ESP_RST_SDIO: return "SDIO";
    default: return "unknown";
    }
}
