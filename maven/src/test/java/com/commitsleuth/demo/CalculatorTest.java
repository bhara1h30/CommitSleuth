package com.commitsleuth.demo;

import static org.junit.jupiter.api.Assertions.*;
import org.junit.jupiter.api.Test;

class CalculatorTest {
    private final Calculator c = new Calculator();
    @Test void addsTwoNumbers() { assertEquals(5, c.add(2, 3)); }
    @Test void subtractsTwoNumbers() { assertEquals(1, c.subtract(3, 2)); }
    @Test void multipliesTwoNumbers() { assertEquals(6, c.multiply(2, 3)); }
    @Test void dividesTwoNumbers() { assertEquals(2, c.divide(6, 3)); }
    @Test void divideByZeroThrows() { assertThrows(IllegalArgumentException.class, () -> c.divide(1, 0)); }
}
