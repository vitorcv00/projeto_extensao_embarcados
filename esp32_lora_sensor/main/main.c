#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_system.h"
#include "esp_event.h"
#include "driver/gpio.h"
#include "nvs_flash.h"
#include "dht11.h"
#include "ttn.h"

#include <stdio.h>
#include <string.h>

#define RESET_DELAY_SEC   30   // tempo em segundos antes de reset
#define TTN_SPI_HOST      SPI2_HOST
#define TTN_SPI_DMA_CHAN  SPI_DMA_DISABLED
#define TTN_PIN_SPI_SCLK  18
#define TTN_PIN_SPI_MOSI  23
#define TTN_PIN_SPI_MISO  19
#define TTN_PIN_NSS       5
#define TTN_PIN_RXTX      TTN_NOT_CONNECTED
#define TTN_PIN_RST       16
#define TTN_PIN_DIO0      26
#define TTN_PIN_DIO1      14

// Chaves TTN
const char *appEui = "0000000000000000";
const char *devEui = "70B3D57ED0070EEA";
const char *appKey = "C2FAEC2119B4498EED86F07FCBF17716";

void messageReceived(const uint8_t *message, size_t length, ttn_port_t port) {
    printf("Message of %d bytes received on port %d:", (int)length, port);
    for (int i = 0; i < length; i++) {
        printf(" %02x", message[i]);
    }
    printf("\n");
}

void app_main(void) {
    esp_err_t err;
    int temperature, humidity;
    char payload[32];
    size_t len;

    // --- Inicializações básicas ---
    ESP_ERROR_CHECK( gpio_install_isr_service(ESP_INTR_FLAG_IRAM) );
    ESP_ERROR_CHECK( nvs_flash_init() );

    spi_bus_config_t spi_bus_config = {
        .miso_io_num = TTN_PIN_SPI_MISO,
        .mosi_io_num = TTN_PIN_SPI_MOSI,
        .sclk_io_num = TTN_PIN_SPI_SCLK,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1
    };
    ESP_ERROR_CHECK( spi_bus_initialize(TTN_SPI_HOST, &spi_bus_config, TTN_SPI_DMA_CHAN) );

    ttn_init();
    ttn_configure_pins(TTN_SPI_HOST,
                       TTN_PIN_NSS,
                       TTN_PIN_RXTX,
                       TTN_PIN_RST,
                       TTN_PIN_DIO0,
                       TTN_PIN_DIO1);
    ttn_provision(devEui, appEui, appKey);
    ttn_on_message(messageReceived);

    // Inicializa DHT11
    DHT11_init(GPIO_NUM_32);

    // Realiza join (sempre que ligar/resetar)
    printf("Joining TTN...\n");
    if (!ttn_join()) {
        printf("Join failed. Abort.\n");
        return;
    }
    printf("Joined TTN network.\n");

    // Faz a leitura do DHT11
    temperature = DHT11_read().temperature;
    humidity    = DHT11_read().humidity;
    printf("Temperatura: %d°C, Humidade: %d%%\n", temperature, humidity);

    // Prepara e envia payload
    len = snprintf(payload, sizeof(payload), "%d %d", temperature, humidity);
    printf("Enviando payload: %s\n", payload);
    ttn_response_code_t res = ttn_transmit_message((uint8_t *)payload, len, 1, false);
    printf(res == TTN_SUCCESSFUL_TRANSMISSION
           ? "Mensagem enviada com sucesso.\n"
           : "Falha na transmissão.\n");

    // Aguarda 30 segundos e reinicia o ESP
    printf("Aguardando %d segundos antes de resetar...\n", RESET_DELAY_SEC);
    vTaskDelay(RESET_DELAY_SEC * 1000 / portTICK_PERIOD_MS);

    printf("Reiniciando ESP...\n");
    esp_restart();
}