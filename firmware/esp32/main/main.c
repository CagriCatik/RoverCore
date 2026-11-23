/*
 * RoverCore VCU firmware - stage 1: safe start-up, enable state machine, diagnostics, watchdog.
 *
 * Tasks:
 *  - control (priority high, core 1): every 5 ms read inputs -> sv_step -> apply outputs -> status LED.
 *    Subscribed to the task watchdog (1 s, panic -> reset -> S0). The supervisor itself flags every step
 *    interval >= 12 ms (EN_FSM_MAX_SAMPLE_GAP_MS) as a fault and falls back to S0.
 *  - diag (priority low, core 0): prints one "RC ..." line per CONFIG_ROVERCORE_DIAG_PERIOD_MS.
 * Actuators: SERVO_PWR_EN / ACT_OE_N stay locked unless CONFIG_ROVERCORE_ACTUATORS_PERMITTED (off in stage 1).
 * Not in this stage: PWM / ESC, RMT LEDs, buzzer tones, IMU, OLED, iBUS (docs/vcu/firmware-plan.md).
 */
#include <stdio.h>
#include <string.h>

#include "esp_log.h"
#include "esp_task_wdt.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "board_io.h"
#include "diag.h"
#include "supervisor.h"

#ifndef CONFIG_ROVERCORE_ACTUATORS_PERMITTED
#define CONFIG_ROVERCORE_ACTUATORS_PERMITTED 0
#endif
#ifndef CONFIG_ROVERCORE_BENCH_DEVKIT_ONLY
#define CONFIG_ROVERCORE_BENCH_DEVKIT_ONLY 0
#endif

#define CONTROL_PERIOD_MS 5u
_Static_assert(CONTROL_PERIOD_MS < EN_FSM_MAX_SAMPLE_GAP_MS, "control period must stay below the gap limit");

static const char *TAG = "rovercore";

static supervisor_t s_sv;
static portMUX_TYPE s_snap_lock = portMUX_INITIALIZER_UNLOCKED;
static struct {
    uint32_t t;
    supervisor_t sv;
    sv_inputs_t in;
    sv_outputs_t out;
} s_snap;

static void control_task(void *arg)
{
    (void)arg;
    ESP_ERROR_CHECK(esp_task_wdt_add(NULL));
    TickType_t wake = xTaskGetTickCount();
    for (;;) {
        sv_inputs_t in;
        bio_read(&in);
        uint32_t now = bio_now_ms();
        sv_outputs_t out = sv_step(&s_sv, now, &in);
        bio_apply(&out);
        bio_status_led(diag_led(&out, s_sv.cfg.actuators_permitted, now));
        portENTER_CRITICAL(&s_snap_lock);
        s_snap.t = now;
        s_snap.sv = s_sv;
        s_snap.in = in;
        s_snap.out = out;
        portEXIT_CRITICAL(&s_snap_lock);
        esp_task_wdt_reset();
        vTaskDelayUntil(&wake, pdMS_TO_TICKS(CONTROL_PERIOD_MS));
    }
}

static void diag_task(void *arg)
{
    (void)arg;
    char line[256];
    for (;;) {
        vTaskDelay(pdMS_TO_TICKS(CONFIG_ROVERCORE_DIAG_PERIOD_MS));
        portENTER_CRITICAL(&s_snap_lock);
        uint32_t t = s_snap.t;
        supervisor_t sv = s_snap.sv;
        sv_inputs_t in = s_snap.in;
        sv_outputs_t out = s_snap.out;
        portEXIT_CRITICAL(&s_snap_lock);
        diag_format(line, sizeof line, t, &sv, &in, &out);
        printf("%s%s\n", line, CONFIG_ROVERCORE_BENCH_DEVKIT_ONLY ? " BENCH" : "");
    }
}

void app_main(void)
{
    /* 1. locked outputs before anything else */
    bio_config_t bcfg = {CONFIG_ROVERCORE_BENCH_DEVKIT_ONLY, CONFIG_ROVERCORE_BENCH_DEVKIT_ONLY};
    int err = bio_safe_init(&bcfg);
    sv_outputs_t locked = sv_locked_outputs();
    bio_apply(&locked);

    ESP_LOGI(TAG, "RoverCore VCU stage 1; reset reason: %s; actuators permitted: %d; bench: %d; io init: %d",
             bio_reset_reason(), CONFIG_ROVERCORE_ACTUATORS_PERMITTED, CONFIG_ROVERCORE_BENCH_DEVKIT_ONLY, err);

    /* 2. supervisor: thresholds are proposals (rev1-versorgung 3.7), not verified values */
    sv_config_t cfg = {.vbat_error_mv = 10500, .vbat_warn_mv = 10800, .vbat_hyst_mv = 200, .vbat_filter_shift = 3,
                       .actuators_permitted = CONFIG_ROVERCORE_ACTUATORS_PERMITTED};
    sv_init(&s_sv, &cfg, bio_now_ms());

    xTaskCreatePinnedToCore(control_task, "control", 4096, NULL, configMAX_PRIORITIES - 2, NULL, 1);
    xTaskCreatePinnedToCore(diag_task, "diag", 4096, NULL, 2, NULL, 0);
}
