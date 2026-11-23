idf_component_register(
    SRCS "main.c"
         "../../app/enable_fsm.c"
         "../../app/supervisor.c"
         "../../app/diag.c"
         "../../bsp/esp32s3/board_io.c"
    INCLUDE_DIRS "." "../../app" "../../bsp/esp32s3"
    REQUIRES driver esp_adc esp_timer freertos)
